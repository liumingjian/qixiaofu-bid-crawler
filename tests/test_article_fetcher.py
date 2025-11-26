import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core.article_fetcher import SougouWeChatFetcher


SAMPLE_LIST_HTML = """
<html>
  <body>
    <ul class="news-list">
      <li>
        <div class="txt-box">
          <h3><a href="https://mp.weixin.qq.com/a">Article A</a></h3>
          <p class="txt-info">Summary A</p>
          <span class="s2">2025-11-25</span>
        </div>
      </li>
      <li>
        <div class="txt-box">
          <h3><a href="https://mp.weixin.qq.com/b">Article B</a></h3>
          <p class="txt-info">Summary B</p>
          <span class="s2">2025-11-24</span>
        </div>
      </li>
    </ul>
  </body>
</html>
""".strip()


class FakeDriver:
    def __init__(self, html: str = "") -> None:
        self._page_source = html
        self.visited: list[str] = []
        self.closed = False
        self.cookies = [{"name": "SUV", "value": "123", "domain": ".sogou.com"}]
        self.added_cookies: list[dict] = []
        self.scroll_heights = [100, 200]
        self.scroll_idx = 0

    def get(self, url: str) -> None:
        self.visited.append(url)

    def execute_script(self, script: str):
        if "document.body.scrollHeight" in script:
            value = self.scroll_heights[min(self.scroll_idx, len(self.scroll_heights) - 1)]
            self.scroll_idx += 1
            return value
        return None

    def add_cookie(self, cookie: dict) -> None:
        self.added_cookies.append(cookie)

    def get_cookies(self):
        return list(self.cookies)

    def quit(self) -> None:
        self.closed = True

    @property
    def page_source(self) -> str:
        return self._page_source

    @page_source.setter
    def page_source(self, value: str) -> None:
        self._page_source = value


class TestSougouWeChatFetcher(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmpdir.name) / "data"
        self.log_dir = Path(self.tmpdir.name) / "logs"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.config = {
            "wechat": {
                "account_name": "测试公众号",
                "max_articles_per_crawl": 5,
            },
            "scraper": {
                "headless": True,
                "wait_time": 0,
                "retry_count": 1,
                "retry_delay": 0,
                "random_delay_range": [0, 0],
                "prompt_on_captcha": False,
            },
            "paths": {
                "data_dir": str(self.data_dir),
                "log_dir": str(self.log_dir),
            },
        }
        self.driver = FakeDriver(SAMPLE_LIST_HTML)
        self.fetcher = SougouWeChatFetcher(config=self.config, driver_factory=lambda: self.driver)

    def tearDown(self) -> None:
        self.fetcher.close()
        for handler in list(self.fetcher.logger.handlers):
            handler.close()
            self.fetcher.logger.removeHandler(handler)
        self.tmpdir.cleanup()

    def test_parse_articles_from_html_supports_news_list_layout(self) -> None:
        articles = self.fetcher._parse_articles_from_html(SAMPLE_LIST_HTML)
        self.assertEqual(2, len(articles))
        self.assertEqual("Article A", articles[0]["title"])
        self.assertIn("2025-11-25", articles[0]["publish_date"])

    @mock.patch("core.article_fetcher.time.sleep", return_value=None)
    def test_save_and_load_cookies_roundtrip(self, _sleep) -> None:
        self.fetcher.driver = self.driver
        self.fetcher._save_cookies()
        self.assertTrue(self.fetcher.cookies_file.exists())

        # Ensure cookies can be loaded back and added to the driver.
        self.driver.added_cookies.clear()
        self.fetcher._load_cookies()
        self.assertGreater(len(self.driver.added_cookies), 0)
        self.assertIn(self.fetcher.base_url, self.driver.visited[0])

    @mock.patch("core.article_fetcher.time.sleep", return_value=None)
    def test_fetch_article_list_deduplicates_and_limits_results(self, _sleep) -> None:
        self.fetcher._random_delay = lambda: None
        with mock.patch.object(self.fetcher, "_search_account", return_value="https://account"):

            def parse_side_effect():
                if not hasattr(parse_side_effect, "called"):
                    parse_side_effect.called = True
                    return [
                        {"title": "A", "url": "u1", "publish_date": "", "digest": ""},
                        {"title": "B", "url": "u2", "publish_date": "", "digest": ""},
                    ]
                return [
                    {"title": "B", "url": "u2", "publish_date": "", "digest": ""},
                    {"title": "C", "url": "u3", "publish_date": "", "digest": ""},
                ]

            with mock.patch.object(self.fetcher, "_parse_articles", side_effect=parse_side_effect):
                with mock.patch.object(self.fetcher, "_scroll_to_load_more", return_value=True):
                    articles = self.fetcher.fetch_article_list(max_articles=3)

        urls = [item["url"] for item in articles]
        self.assertEqual(["u1", "u2", "u3"], urls)


if __name__ == "__main__":
    unittest.main()
