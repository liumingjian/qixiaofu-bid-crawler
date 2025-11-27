"""Multi-source crawler that aggregates articles from multiple WeChat accounts."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Optional

from core.article_fetcher import SougouWeChatFetcher
from models.wechat_account import WeChatAccount


class MultiSourceCrawler:
    """Orchestrates crawling from multiple WeChat accounts."""
    
    def __init__(
        self,
        config: Mapping[str, Any],
        logger=None,
        session_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.config = config
        self.logger = logger
        self.session_factory = session_factory
    
    def fetch_all_articles(self, max_articles: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch articles from all enabled WeChat accounts.
        
        Returns:
            List of article dicts with an added 'source_account_id' field.
        """
        all_articles = []
        accounts = self._load_accounts()
        
        if not accounts:
            if self.logger:
                self.logger.warning("No WeChat accounts configured")
            return []
        
        for account in accounts:
            try:
                articles = self._fetch_from_account(account, max_articles)
                for article in articles:
                    article["source_account_id"] = account.get("id", "unknown")
                    article["source_account_name"] = account.get("name", "Unknown")
                all_articles.extend(articles)
                
                if self.logger:
                    self.logger.info(
                        f"Fetched {len(articles)} articles from account '{account.get('name')}'"
                    )
            except Exception as exc:
                if self.logger:
                    self.logger.error(
                        f"Failed to fetch from account '{account.get('name')}': {exc}",
                        exc_info=True
                    )
        
        return all_articles
    
    def _load_accounts(self) -> List[Dict[str, Any]]:
        """Load WeChat account configurations from DB or config fallback."""
        if self.session_factory is not None:
            session = self.session_factory()
            try:
                records = WeChatAccount.get_all(session, enabled_only=True)
                return [record.to_dict() for record in records]
            finally:
                session.close()
        
        wechat_cfg = self.config.get("wechat", {})
        accounts = []
        for account in wechat_cfg.get("accounts", []):
            if not account.get("enabled", True):
                continue
            accounts.append(account)
        return accounts
    
    def _fetch_from_account(
        self, 
        account: Dict[str, Any], 
        max_articles: int
    ) -> List[Dict[str, Any]]:
        """Fetch articles from a single account."""
        account_config = dict(self.config)
        account_config["wechat"] = {
            **self.config.get("wechat", {}),
            "fakeid": account.get("fakeid", ""),
            "token": account.get("token", ""),
            "cookie": account.get("cookie", ""),
            "page_size": account.get("page_size", 5),
            "days_limit": account.get("days_limit", 7),
            "filter_keywords": account.get("filter_keywords"),
            "filter_keyword_logic": account.get("filter_keyword_logic"),
        }
        
        fetcher = SougouWeChatFetcher(
            config_path="config.yml",  # Path not used, config is passed
            config=account_config,
            logger=self.logger
        )
        
        return fetcher.fetch_article_list(max_articles=max_articles)
