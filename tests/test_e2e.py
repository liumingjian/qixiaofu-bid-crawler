import json
import tempfile
import unittest
from pathlib import Path

from app import CrawlRunner
from core.bid_extractor import BidInfoExtractor
from core.data_manager import DataManager
from utils.logger import setup_logger


SAMPLE_TEXT = """
1项目名称：示例项目一
预算金额：50万元
采购人：示例单位A
获取采购文件：2025年12月01日
项目编号：A-001
服务期限：1年
采购内容：示例内容

2项目名称：示例项目二
预算金额：80万元
采购人：示例单位B
获取采购文件：2025年12月05日
项目编号：B-002
服务期限：2年
采购内容：示例内容
"""


class FakeFetcher:
    def fetch_article_list(self, max_articles=50):
        return [
            {"url": "https://example.com/a", "title": "Article A"},
            {"url": "https://example.com/b", "title": "Article B"},
        ]


class FakeScraper:
    def scrape_articles_batch(self, urls, callback=None):
        articles = []
        total = len(urls)
        for idx, url in enumerate(urls, 1):
            article = {
                "url": url,
                "title": f"Article {idx}",
                "content_text": SAMPLE_TEXT,
                "content_html": "<div></div>",
            }
            articles.append(article)
            if callback:
                callback(idx, total, article)
        return articles


class FakeNotifier:
    def __init__(self):
        self.calls = []

    def send_bid_notification(self, bids, data_manager):
        self.calls.append(bids)
        for bid in bids:
            bid_id = bid.get("id")
            if bid_id:
                data_manager.update_bid_status(bid_id, "notified")
        return True


class CrawlRunnerIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmpdir.name) / "data"
        self.log_dir = Path(self.tmpdir.name) / "logs"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.config_path = Path(self.tmpdir.name) / "config.json"
        config = {
            "paths": {"data_dir": str(self.data_dir), "log_dir": str(self.log_dir)},
            "wechat": {"account_name": "测试号", "max_articles_per_crawl": 3},
            "email": {
                "smtp_server": "smtp.test",
                "smtp_port": 587,
                "sender_email": "bot@example.com",
                "sender_password": "secret",
                "recipient_emails": ["tester@example.com"],
            },
            "scraper": {"headless": True},
        }
        self.config_path.write_text(json.dumps(config), encoding="utf-8")
        self.config = config

        self.logger = setup_logger("IntegrationTest", log_dir=self.log_dir)
        self.data_manager = DataManager(str(self.config_path))

    def tearDown(self) -> None:
        for handler in list(self.data_manager.logger.handlers):
            handler.close()
            self.data_manager.logger.removeHandler(handler)
        for handler in list(self.logger.handlers):
            handler.close()
            self.logger.removeHandler(handler)
        self.tmpdir.cleanup()

    def test_runner_persists_bids_and_notifies(self):
        runner = CrawlRunner(
            self.config,
            data_manager=self.data_manager,
            fetcher=FakeFetcher(),
            scraper=FakeScraper(),
            extractor=BidInfoExtractor(logger=self.logger),
            notifier=FakeNotifier(),
            logger=self.logger,
        )

        status = {"is_running": True, "progress": 0, "total": 0, "message": ""}

        def update_status(**kwargs):
            status.update(kwargs)

        runner.run(status, update_status)

        bids = self.data_manager.get_all_bids()
        self.assertGreaterEqual(len(bids), 2)
        self.assertEqual("notified", bids[0]["status"])

        notifier = runner.notifier
        self.assertEqual(1, len(notifier.calls))
        self.assertGreaterEqual(len(notifier.calls[0]), 2)

        articles_file = self.data_dir / "articles.json"
        self.assertTrue(articles_file.exists())

        self.assertIn("爬取完成", status["message"])


if __name__ == "__main__":
    unittest.main()
