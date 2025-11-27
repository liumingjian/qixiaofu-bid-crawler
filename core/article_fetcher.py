"""WeChat official account article list fetcher using the MP backend API."""

from __future__ import annotations

import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Mapping, MutableMapping, Optional, Sequence, Tuple

import requests

from utils.config_loader import load_config
from utils.logger import setup_logger

ArticleData = MutableMapping[str, str]


class SougouWeChatFetcher:
    """
    Fetch article metadata by calling the https://mp.weixin.qq.com/cgi-bin/appmsg API.

    The name is kept for backwards compatibility, but the implementation now relies on
    manual cookie/token/fakeid credentials extracted from the WeChat public platform.
    """

    base_url = "https://mp.weixin.qq.com/cgi-bin/appmsg"
    DEFAULT_KEYWORDS: Sequence[str] = ("招标", "采购", "询价", "谈判", "磋商", "竞价")

    def __init__(
        self,
        config_path: str | Path = "config.yml",
        *,
        config: Optional[Mapping[str, Any]] = None,
        session: Optional[requests.Session] = None,
        logger=None,
    ) -> None:
        self.config_path = Path(config_path)
        self.config = dict(config) if config else self._load_config(self.config_path)

        wechat_cfg = self.config.get("wechat", {})
        paths_cfg = self.config.get("paths", {})

        self.account_name = wechat_cfg.get("account_name", "")
        self.max_articles = int(wechat_cfg.get("max_articles_per_crawl", 50) or 0)
        self.fakeid = str(wechat_cfg.get("fakeid", "")).strip()
        self.token = str(wechat_cfg.get("token", "")).strip()
        self.cookie = str(wechat_cfg.get("cookie", "")).strip()
        self.user_agent = str(
            wechat_cfg.get(
                "user_agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
        )
        self.page_size = max(1, int(wechat_cfg.get("page_size", 5) or 5))
        self.article_limit = int(wechat_cfg.get("article_limit", 10) or 10)

        # New: Filtering logic
        self.keyword_logic = str(wechat_cfg.get("filter_keyword_logic", "OR")).upper()
        if self.keyword_logic not in ("AND", "OR"):
            self.keyword_logic = "OR"

        # Simplified fetch mode - always fetch by count
        self.fetch_mode: str = "latest_count"
        self.fetch_rule_value: int = self.article_limit
        self._configure_fetch_rule(wechat_cfg.get("fetch_rule", {}))
        
        # Overrides from constructor config (e.g. from multi_source_crawler passing account details)
        if config and "filter_keyword_logic" in wechat_cfg:
             self.keyword_logic = wechat_cfg["filter_keyword_logic"]
        if config and "filter_keywords" in wechat_cfg:
             # If passed explicitly (e.g. from account DB), use it
             self.keyword_filters = self._normalize_keywords(wechat_cfg["filter_keywords"])
        else:
             # Fallback to global config
             keywords = wechat_cfg.get("keyword_filters")
             self.keyword_filters = self._normalize_keywords(keywords)

        rate_limit_wait = wechat_cfg.get("rate_limit_wait")
        self.rate_limit_wait = int(rate_limit_wait) if rate_limit_wait is not None else 60
        self.request_timeout = int(wechat_cfg.get("request_timeout", 10) or 10)
        self.retry_count = max(1, int(wechat_cfg.get("retry_count", 3) or 3))
        self.retry_delay = max(0, int(wechat_cfg.get("retry_delay", 5) or 5))

        interval = wechat_cfg.get("request_interval_range", (5, 10))
        if (
            not isinstance(interval, Sequence)
            or isinstance(interval, (str, bytes))
            or len(interval) != 2
        ):
            interval = (5, 10)
        start, end = float(interval[0]), float(interval[1])
        if end < start:
            start, end = end, start
        self.request_interval_range: Sequence[float] = (start, end)

        log_dir = Path(paths_cfg.get("log_dir", "data/logs"))
        log_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logger or setup_logger(self.__class__.__name__, log_dir=log_dir)
        self.session = session or requests.Session()

    def _load_config(self, path: Path) -> Mapping[str, Any]:
        return load_config(path)

    def fetch_article_list(self, max_articles: Optional[int] = None) -> List[ArticleData]:
        """
        Return article metadata filtered by keywords.
        Fetches the most recent N articles (after keyword filtering).
        """
        limit = self._resolve_limit(max_articles)
        if limit <= 0:
            return []

        if not self._has_credentials():
            self.logger.error("WeChat fakeid/token/cookie configuration is incomplete.")
            return []

        articles: List[ArticleData] = []
        begin = 0

        self.logger.info(
            "Fetching articles via WeChat API. account=%s max=%d",
            self.account_name or self.fakeid,
            limit,
        )

        while len(articles) < limit:
            payload = self._request_with_retry(begin)
            if not payload:
                break

            items = payload.get("app_msg_list") or []
            if not items:
                break

            for item in items:
                # Check keyword filter
                if not self._match_keywords(item.get("title", "")):
                    continue

                article = self._normalize_article(item)
                if not article:
                    continue
                articles.append(article)
                if len(articles) >= limit:
                    break

            begin += self.page_size
            self._random_delay()

        self.logger.info("Collected %d article(s) from WeChat backend.", len(articles))
        return articles[:limit]

    def _configure_fetch_rule(self, rule_cfg: Mapping[str, Any] | None) -> None:
        """Configure fetch rule - now only supports article count."""
        if not rule_cfg:
            return
        mode = str(rule_cfg.get("mode", "")).strip().lower()
        value = int(rule_cfg.get("value", 0) or 0)
        # Only support latest_count mode now
        if mode == "latest_count" and value > 0:
            self.fetch_mode = mode
            self.fetch_rule_value = value
            self.article_limit = value

    def _resolve_limit(self, override: Optional[int]) -> int:
        if override and override > 0:
            return override
        return self.article_limit

    def _request_with_retry(self, begin: int) -> Optional[Mapping[str, Any]]:
        for attempt in range(1, self.retry_count + 1):
            payload = self._request_page(begin)
            if payload is not None:
                return payload
            if attempt < self.retry_count and self.retry_delay:
                self.logger.info(
                    "Retrying article list request in %ds (attempt %d/%d).",
                    self.retry_delay,
                    attempt + 1,
                    self.retry_count,
                )
                time.sleep(self.retry_delay)
        return None

    def _request_page(self, begin: int) -> Optional[Mapping[str, Any]]:
        params = {
            "token": self.token,
            "lang": "zh_CN",
            "f": "json",
            "ajax": "1",
            "action": "list_ex",
            "begin": str(begin),
            "count": str(self.page_size),
            "query": "",
            "fakeid": self.fakeid,
            "type": "9",
        }
        headers = {
            "Cookie": self.cookie,
            "User-Agent": self.user_agent,
            "Referer": "https://mp.weixin.qq.com/",
        }

        try:
            response = self.session.get(
                self.base_url, headers=headers, params=params, timeout=self.request_timeout
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            self.logger.error("Failed to request article list (begin=%s): %s", begin, exc)
            return None

        try:
            payload = response.json()
        except ValueError as exc:
            self.logger.error("Invalid JSON payload from WeChat API: %s", exc)
            return None

        base_resp = payload.get("base_resp", {})
        ret = base_resp.get("ret", 0)
        if ret == 0:
            return payload

        if ret == 200013:
            self.logger.warning("Hit WeChat rate limit (ret=200013). Waiting %ds.", self.rate_limit_wait)
            if self.rate_limit_wait > 0:
                time.sleep(self.rate_limit_wait)
            return None

        if ret == 200003:
            self.logger.error("WeChat cookie/token expired (ret=200003). Please refresh credentials.")
            return None

        self.logger.error("WeChat API returned error ret=%s msg=%s", ret, base_resp)
        return None

    def _normalize_article(self, item: Mapping[str, Any]) -> Optional[ArticleData]:
        url = str(item.get("link", "")).strip()
        if not url:
            return None
        timestamp = item.get("create_time")
        publish_date = ""
        if isinstance(timestamp, (int, float)):
            publish_date = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()

        return {
            "title": str(item.get("title", "")).strip(),
            "url": url,
            "publish_date": publish_date,
            "digest": str(item.get("digest", "")).strip(),
        }

    def _match_keywords(self, title: str) -> bool:
        if not self.keyword_filters:
            return True
        normalized = str(title or "")
        
        if self.keyword_logic == "AND":
             # All keywords must be present
             return all(keyword in normalized for keyword in self.keyword_filters)
        
        # Default OR: Any keyword matches
        return any(keyword in normalized for keyword in self.keyword_filters)

    def _random_delay(self) -> None:
        start, end = self.request_interval_range
        if end <= 0:
            return
        delay = random.uniform(start, end)
        if delay <= 0:
            return
        self.logger.debug("Sleeping for %.2fs before next WeChat request.", delay)
        time.sleep(delay)

    def _normalize_keywords(self, keywords: Any) -> List[str]:
        if not keywords:
            return list(self.DEFAULT_KEYWORDS)
        if isinstance(keywords, (str, bytes)):
            candidate = keywords.decode("utf-8") if isinstance(keywords, bytes) else keywords
            value = candidate.strip()
            return [value] if value else []

        normalized: List[str] = []
        for keyword in keywords:
            kw = str(keyword).strip()
            if kw:
                normalized.append(kw)
        return normalized

    def _has_credentials(self) -> bool:
        return bool(self.fakeid and self.token and self.cookie)

    def validate_credentials(self) -> Tuple[bool, str]:
        """
        Validate the current credentials by making a lightweight API call.
        Returns:
            (is_valid, error_message)
        """
        if not self._has_credentials():
            return False, "缺少必要参数 (fakeid, token, cookie)"

        # Try to fetch the first page with a small count to verify credentials
        # We use a separate method or just reuse _request_page but we need to handle the response carefully.
        # To avoid affecting the main crawl state, we just do a single request.
        
        # We can use _request_page(0) but we need to ensure we don't trigger rate limits unnecessarily.
        # Ideally, we just want to check if the token/cookie is valid.
        
        try:
            # Re-using _request_page logic but explicitly handling the response here
            # to provide better error messages.
            # We temporarily set page_size to 1 to minimize data transfer
            original_page_size = self.page_size
            self.page_size = 1
            try:
                payload = self._request_page(0)
            finally:
                self.page_size = original_page_size

            if payload is not None:
                return True, "验证成功"

            if payload is None:
                # _request_page returns None on error, but logs it. 
                # We can't easily get the exact error message from _request_page without refactoring,
                # so we might need to duplicate some logic or rely on the logs (which isn't good for UI feedback).
                # Let's look at _request_page again. It handles retries and logging.
                # For validation, we might want to call the API directly or refactor _request_page.
                # However, for minimal invasion, let's try to interpret the result.
                # If _request_page returns None, it's likely a failure.
                
                # Actually, let's just make a direct call here to be sure and get the error code.
                params = {
                    "token": self.token,
                    "lang": "zh_CN",
                    "f": "json",
                    "ajax": "1",
                    "action": "list_ex",
                    "begin": "0",
                    "count": "1",
                    "query": "",
                    "fakeid": self.fakeid,
                    "type": "9",
                }
                headers = {
                    "Cookie": self.cookie,
                    "User-Agent": self.user_agent,
                    "Referer": "https://mp.weixin.qq.com/",
                }
                
                response = self.session.get(
                    self.base_url, headers=headers, params=params, timeout=self.request_timeout
                )
                response.raise_for_status()
                data = response.json()
                
                base_resp = data.get("base_resp", {})
                ret = base_resp.get("ret", 0)
                
                if ret == 0:
                    return True, "验证成功"
                elif ret == 200003:
                    return False, "Cookie或Token已过期 (ret=200003)"
                elif ret == 200013:
                    return False, "触发微信频率限制 (ret=200013)，请稍后再试"
                else:
                    return False, f"验证失败: 微信API返回错误 {ret} ({base_resp.get('err_msg', '未知错误')})"

        except requests.RequestException as exc:
            return False, f"网络请求失败: {str(exc)}"
        except ValueError:
            return False, "微信API返回了无效的JSON数据"
        except Exception as exc:
            return False, f"验证过程发生未知错误: {str(exc)}"
