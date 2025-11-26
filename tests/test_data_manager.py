import tempfile
import unittest
from pathlib import Path

from core.data_manager import DataManager
from core.database import Database
from storage.file_storage import FileStorage
from utils.config_loader import dump_config


class TestFileStorage(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.storage = FileStorage()
        self.data_path = Path(self.tmpdir.name) / "data.json"

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_load_missing_returns_empty_list(self) -> None:
        self.assertEqual([], self.storage.load_json(self.data_path))

    def test_save_creates_backup_on_overwrite(self) -> None:
        self.assertTrue(self.storage.save_json(self.data_path, [{"id": 1}]))
        self.assertEqual(0, len(list(self.data_path.parent.glob("data.json.*.bak"))))

        self.assertTrue(self.storage.save_json(self.data_path, [{"id": 2}]))
        backups = list(self.data_path.parent.glob("data.json.*.bak"))
        self.assertEqual(1, len(backups))

    def test_corrupt_file_is_quarantined(self) -> None:
        self.data_path.write_text("{bad json", encoding="utf-8")
        result = self.storage.load_json(self.data_path)
        self.assertEqual([], result)
        self.assertFalse(self.data_path.exists())
        quarantined = list(self.data_path.parent.glob("data.json.*.corrupt"))
        self.assertEqual(1, len(quarantined))


class TestDataManager(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        tmp_path = Path(self.tmpdir.name)
        shared_log_dir = Path("data/logs").resolve()
        shared_log_dir.mkdir(parents=True, exist_ok=True)
        config = {
            "paths": {
                "data_dir": str(tmp_path / "data"),
                "log_dir": str(shared_log_dir),
            }
        }
        self.config_path = tmp_path / "config.yml"
        dump_config(self.config_path, config)
        self.manager = DataManager(str(self.config_path))

    def tearDown(self) -> None:
        if hasattr(self, "manager"):
            for handler in list(self.manager.logger.handlers):
                handler.close()
                self.manager.logger.removeHandler(handler)
        self.tmpdir.cleanup()

    def _sample_bid(self, suffix: int, **overrides) -> dict:
        bid = {
            "id": f"bid-{suffix}",
            "project_name": f"Project {suffix}",
            "budget": f"{suffix}万元",
            "purchaser": f"Purchaser {suffix}",
            "doc_time": "2025-11-25",
            "status": "new",
        }
        bid.update(overrides)
        return bid

    def test_save_bids_deduplicates(self) -> None:
        bid = self._sample_bid(1)
        self.assertEqual(1, len(self.manager.save_bids([bid])))
        self.assertEqual(0, len(self.manager.save_bids([bid])))

        stored = self.manager.get_all_bids()
        self.assertEqual(1, len(stored))
        self.assertEqual("bid-1", stored[0]["id"])

    def test_get_bids_by_status(self) -> None:
        bids = [
            self._sample_bid(1, status="new"),
            self._sample_bid(2, status="notified"),
            self._sample_bid(3, status="archived"),
        ]
        self.manager.save_bids(bids)

        new_bids = self.manager.get_all_bids(status="new")
        self.assertEqual(1, len(new_bids))
        self.assertEqual("bid-1", new_bids[0]["id"])

    def test_update_bid_status(self) -> None:
        bid = self._sample_bid(5)
        self.manager.save_bids([bid])
        updated = self.manager.update_bid_status("bid-5", "notified")
        self.assertTrue(updated)
        stored = self.manager.get_all_bids(status="notified")
        self.assertEqual(1, len(stored))
        self.assertEqual("notified", stored[0]["status"])

    def test_article_save_and_deduplication(self) -> None:
        article = {
            "url": "https://example.com/article-1",
            "title": "Article",
            "author": "Tester",
            "publish_time": "2025-11-25",
        }
        self.assertTrue(self.manager.save_article(article))
        self.assertFalse(self.manager.save_article(article))
        self.assertTrue(self.manager.is_article_crawled(article["url"]))

    def test_stats_summary(self) -> None:
        self.manager.save_article({"url": "https://a.com"})
        self.manager.save_article({"url": "https://b.com"})

        bids = [
            self._sample_bid(1, status="new"),
            self._sample_bid(2, status="notified"),
            self._sample_bid(3, status="archived"),
        ]
        self.manager.save_bids(bids)

        stats = self.manager.get_stats()
        self.assertEqual(2, stats["total_articles"])
        self.assertEqual(3, stats["total_bids"])
        self.assertEqual(1, stats["new_bids"])
        self.assertEqual(1, stats["notified_bids"])
        self.assertEqual(1, stats["archived_bids"])


class TestDataManagerDatabase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        tmp_path = Path(self.tmpdir.name)
        log_dir = Path(self.tmpdir.name) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = tmp_path / "bids.sqlite"
        self.config = {
            "paths": {
                "data_dir": str(tmp_path / "data"),
                "log_dir": str(log_dir),
            },
            "database": {
                "enabled": True,
                "url": f"sqlite:///{self.db_path}",
            },
        }
        self.config_path = tmp_path / "config.yml"
        dump_config(self.config_path, self.config)
        self.database = Database(self.config)
        self.database.create_tables()
        self.manager = DataManager(
            str(self.config_path),
            config=self.config,
            db_session_factory=self.database.get_session_factory(),
        )

    def tearDown(self) -> None:
        if hasattr(self, "manager"):
            for handler in list(self.manager.logger.handlers):
                handler.close()
                self.manager.logger.removeHandler(handler)
        self.tmpdir.cleanup()

    def _sample_bid(self, suffix: int, **overrides) -> dict:
        payload = {
            "id": f"db-bid-{suffix}",
            "project_name": f"DB Project {suffix}",
            "budget": f"{suffix}万元",
            "purchaser": f"Purchaser {suffix}",
            "doc_time": "2025-12-01",
            "status": "new",
        }
        payload.update(overrides)
        return payload

    def test_bid_crud_in_database(self) -> None:
        bid = self._sample_bid(1)
        created = self.manager.save_bids([bid])
        self.assertEqual(1, len(created))
        self.assertEqual(0, len(self.manager.save_bids([bid])))

        notified = self.manager.update_bid_status("db-bid-1", "notified")
        self.assertTrue(notified)
        stored = self.manager.get_all_bids(status="notified")
        self.assertEqual(1, len(stored))

    def test_article_and_stats_in_database(self) -> None:
        article = {
            "url": "https://db-example.com/a",
            "title": "DB Article",
            "author": "Tester",
        }
        self.assertTrue(self.manager.save_article(article))
        self.assertFalse(self.manager.save_article(article))

        bids = [
            self._sample_bid(1, status="new"),
            self._sample_bid(2, status="notified"),
        ]
        self.manager.save_bids(bids)

        stats = self.manager.get_stats()
        self.assertEqual(1, stats["total_articles"])
        self.assertEqual(2, stats["total_bids"])
        self.assertEqual(1, stats["new_bids"])
        self.assertEqual(1, stats["notified_bids"])


if __name__ == "__main__":
    unittest.main()
