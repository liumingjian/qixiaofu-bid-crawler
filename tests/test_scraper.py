import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core.scraper import WeChatArticleScraper


SAMPLE_HTML = """
<html>
<body>
    <h1 class="rich_media_title">Sample Title</h1>
    <a class="rich_media_meta_link">Author</a>
    <em id="publish_time">2025-11-25</em>
    <div id="js_content">
        <p>Paragraph 1</p>
        <p>Paragraph 2</p>
        <img data-src="https://example.com/image1.png" />
    </div>
</body>
</html>
""".strip()


class FakeDriver:
    def __init__(self, html=SAMPLE_HTML):
        self._page_source = html
        self.visited = []
        self.closed = False

    def get(self, url):
        self.visited.append(url)

    def execute_script(self, script):
        if "document.body.scrollHeight" in script:
            return 1000
        if "window.innerHeight" in script:
            return 500
        return None

    def quit(self):
        self.closed = True

    @property
    def page_source(self):
        return self._page_source

    @page_source.setter
    def page_source(self, value):
        self._page_source = value


class TestWeChatArticleScraper(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.config = {
            "scraper": {
                "headless": True,
                "wait_time": 0,
                "retry_count": 3,
                "retry_delay": 0,
                "random_delay_range": [0, 0],
            },
            "paths": {
                "log_dir": str(Path(self.tmpdir.name) / "logs"),
            },
        }
        self._scrapers: list[WeChatArticleScraper] = []

    def tearDown(self) -> None:
        for scraper in self._scrapers:
            scraper.close()
            for handler in list(scraper.logger.handlers):
                handler.close()
                scraper.logger.removeHandler(handler)
        self.tmpdir.cleanup()

    def make_scraper(self):
        scraper = WeChatArticleScraper(
            config=self.config,
            driver_factory=lambda: FakeDriver(),
        )
        self._scrapers.append(scraper)
        return scraper

    @mock.patch("core.scraper.time.sleep", return_value=None)
    def test_scrape_article_parses_basic_fields(self, _sleep) -> None:
        scraper = self.make_scraper()
        with mock.patch.object(scraper, "_wait_for_content"):
            data = scraper.scrape_article("https://example.com/article")
        self.assertEqual("Sample Title", data["title"])
        self.assertEqual("Author", data["author"])
        self.assertIn("Paragraph 1", data["content_text"])
        scraper.close()

    @mock.patch("core.scraper.time.sleep", return_value=None)
    def test_batch_scrape_invokes_callback(self, _sleep) -> None:
        scraper = self.make_scraper()
        scraper._random_delay = lambda: None  # skip random wait
        results = []

        def callback(index, total, data):
            results.append((index, total, data["url"]))

        with mock.patch.object(
            scraper,
            "_scrape_with_retry",
            side_effect=[
                {"url": "a", "content_text": "x"},
                None,
                {"url": "b", "content_text": "y"},
            ],
        ) as mock_retry:
            articles = scraper.scrape_articles_batch(["a", "b", "c"], callback=callback)

        self.assertEqual(2, len(articles))
        self.assertEqual(2, len(results))
        self.assertEqual(3, mock_retry.call_count)
        scraper.close()

    @mock.patch("core.scraper.time.sleep", return_value=None)
    def test_retry_logic_attempts_until_success(self, sleep_mock) -> None:
        scraper = self.make_scraper()
        scraper.scrape_article = mock.MagicMock(
            side_effect=[None, {"content_text": ""}, {"content_text": "ok"}]
        )
        result = scraper._scrape_with_retry("https://example.com")
        self.assertEqual({"content_text": "ok"}, result)
        self.assertEqual(3, scraper.scrape_article.call_count)
        self.assertEqual(2, sleep_mock.call_count)  # two waits before success
        scraper.close()

    def test_close_handles_missing_driver(self) -> None:
        scraper = self.make_scraper()
        driver = scraper.init_driver()
        self.assertFalse(driver.closed)
        scraper.close()
        self.assertIsNone(scraper.driver)
        self.assertTrue(driver.closed)


if __name__ == "__main__":
    unittest.main()
