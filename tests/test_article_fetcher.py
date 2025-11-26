import json
import tempfile
import time
import unittest
from pathlib import Path

import requests

from core.article_fetcher import SougouWeChatFetcher


class FakeResponse:
    def __init__(self, payload, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses: dict[int, dict]) -> None:
        self.responses = responses
        self.calls: list[int] = []

    def get(self, url, headers=None, params=None, timeout=None):
        begin = int(params.get("begin", 0))
        self.calls.append(begin)
        payload = self.responses.get(begin)
        if isinstance(payload, Exception):
            raise payload
        if payload is None:
            raise AssertionError(f"Unexpected begin offset: {begin}")
        return FakeResponse(payload)


class TestSougouWeChatFetcher(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmpdir.name) / "data"
        self.log_dir = Path(self.tmpdir.name) / "logs"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.config = {
            "wechat": {
                "account_name": "测试公众号",
                "max_articles_per_crawl": 5,
                "fakeid": "FAKEID",
                "token": "TOKEN",
                "cookie": "SOME_COOKIE=1;",
                "user_agent": "pytest",
                "page_size": 5,
                "days_limit": 30,
                "keyword_filters": ["招标", "采购"],
                "request_interval_range": [0, 0],
                "rate_limit_wait": 0,
                "retry_delay": 0,
                "retry_count": 1,
            },
            "paths": {
                "data_dir": str(self.data_dir),
                "log_dir": str(self.log_dir),
            },
        }

    def tearDown(self) -> None:
        logger = getattr(self, "fetcher_logger", None)
        if logger:
            for handler in list(logger.handlers):
                handler.close()
                logger.removeHandler(handler)
        self.tmpdir.cleanup()

    def _build_fetcher(self, session: FakeSession) -> SougouWeChatFetcher:
        fetcher = SougouWeChatFetcher(config=self.config, session=session)
        self.fetcher_logger = fetcher.logger
        return fetcher

    def test_fetch_article_list_filters_by_keywords_and_cutoff(self) -> None:
        now = int(time.time())
        responses = {
            0: {
                "base_resp": {"ret": 0},
                "app_msg_list": [
                    {
                        "title": "公司动态",
                        "link": "https://example.com/a",
                        "digest": "无关",
                        "create_time": now,
                    },
                    {
                        "title": "采购项目A",
                        "link": "https://example.com/b",
                        "digest": "包含采购",
                        "create_time": now,
                    },
                ],
            },
            5: {
                "base_resp": {"ret": 0},
                "app_msg_list": [
                    {
                        "title": "招标项目B",
                        "link": "https://example.com/c",
                        "digest": "有效",
                        "create_time": now - 5 * 86400,
                    },
                    {
                        "title": "历史文章",
                        "link": "https://example.com/d",
                        "digest": "",
                        "create_time": now - 90 * 86400,
                    },
                ],
            },
        }

        fetcher = self._build_fetcher(FakeSession(responses))
        fetcher.days_limit = 10

        articles = fetcher.fetch_article_list(max_articles=5)
        self.assertEqual(2, len(articles))
        self.assertEqual("采购项目A", articles[0]["title"])
        self.assertEqual("招标项目B", articles[1]["title"])
        self.assertTrue(articles[0]["publish_date"].startswith("20"))

    def test_returns_empty_when_wechat_session_invalid(self) -> None:
        responses = {
            0: {
                "base_resp": {"ret": 200003},
                "app_msg_list": [],
            }
        }
        fetcher = self._build_fetcher(FakeSession(responses))
        articles = fetcher.fetch_article_list(max_articles=5)
        self.assertEqual([], articles)


if __name__ == "__main__":
    unittest.main()
