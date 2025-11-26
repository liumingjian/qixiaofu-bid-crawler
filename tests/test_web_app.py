import tempfile
import unittest
from pathlib import Path

from app import CrawlRunner, CrawlController, create_app


class FakeDataManager:
    def __init__(self):
        self.bids = [
            {"id": "1", "project_name": "A", "budget": "10万元", "purchaser": "X", "doc_time": "2025-01-01", "status": "new", "source_url": "#"},
            {"id": "2", "project_name": "B", "budget": "20万元", "purchaser": "Y", "doc_time": "2025-01-02", "status": "notified", "source_url": "#"},
        ]
        self.stats = {
            "total_articles": 5,
            "total_bids": 2,
            "new_bids": 1,
            "notified_bids": 1,
            "archived_bids": 0,
        }

    def get_all_bids(self, status=None):
        if status:
            return [bid for bid in self.bids if bid["status"] == status]
        return list(self.bids)

    def get_stats(self):
        return dict(self.stats)


class FakeCrawlRunner:
    def __init__(self):
        self.runs = 0

    def run(self, status, update_status):
        self.runs += 1
        update_status(total=2, progress=1, message="进行中")
        update_status(progress=2, message="已完成")


class WebAppTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        log_dir = Path(self.tmpdir.name) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(self.tmpdir.name) / "webapp.sqlite"
        self.config = {
            "paths": {"log_dir": str(log_dir)},
            "wechat": {"account_name": "测试号", "max_articles_per_crawl": 5},
            "database": {"url": f"sqlite:///{self.db_path}"},
        }
        self.data_manager = FakeDataManager()
        self.runner = FakeCrawlRunner()
        self.app = create_app(
            config=self.config,
            data_manager=self.data_manager,
            crawl_runner=self.runner,
            controller_executor=lambda func: func(),  # synchronous for tests
        )
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        logger = self.app.config.get("LOGGER")
        if logger:
            for handler in list(logger.handlers):
                handler.close()
                logger.removeHandler(handler)
        self.tmpdir.cleanup()

    def test_get_bids_filters_status(self):
        response = self.client.get("/api/bids?status=new")
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(1, payload["count"])
        self.assertEqual("A", payload["data"][0]["project_name"])

    def test_start_crawl_updates_status(self):
        response = self.client.post("/api/crawl/start")
        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertTrue(payload["success"])

        status_resp = self.client.get("/api/crawl/status")
        status = status_resp.get_json()["data"]
        self.assertFalse(status["is_running"])
        self.assertIn("已完成", status["message"])
        self.assertEqual(1, self.runner.runs)

    def test_stats_endpoint_returns_data(self):
        response = self.client.get("/api/stats")
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(2, payload["data"]["total_bids"])

    def test_index_page_renders(self):
        response = self.client.get("/")
        self.assertEqual(200, response.status_code)
        self.assertIn("招标信息爬虫系统", response.get_data(as_text=True))


class WebAppDatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        log_dir = Path(self.tmpdir.name) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(self.tmpdir.name) / "accounts.db"
        self.config = {
            "paths": {"log_dir": str(log_dir)},
            "wechat": {"account_name": "测试号", "max_articles_per_crawl": 5},
            "database": {
                "url": f"sqlite:///{self.db_path}",
            },
        }
        self.data_manager = FakeDataManager()
        self.runner = FakeCrawlRunner()
        self.app = create_app(
            config=self.config,
            data_manager=self.data_manager,
            crawl_runner=self.runner,
            controller_executor=lambda func: func(),
        )
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        logger = self.app.config.get("LOGGER")
        if logger:
            for handler in list(logger.handlers):
                handler.close()
                logger.removeHandler(handler)
        self.tmpdir.cleanup()

    def test_wechat_account_crud_via_database(self):
        response = self.client.get("/api/sources/wechat")
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertGreaterEqual(len(payload["data"]), 1)

        new_account = {
            "name": "新增账号",
            "fakeid": "FAKE2",
            "token": "TOKEN2",
            "cookie": "COOKIE=2;",
            "page_size": 6,
            "days_limit": 10,
            "enabled": True,
        }
        create_resp = self.client.post("/api/sources/wechat", json=new_account)
        created = create_resp.get_json()
        self.assertTrue(created["success"])
        created_account = created["data"]
        self.assertEqual("新增账号", created_account["name"])

        update_resp = self.client.put(
            f"/api/sources/wechat/{created_account['id']}",
            json={"enabled": False, "page_size": 9},
        )
        updated = update_resp.get_json()
        self.assertTrue(updated["success"])
        self.assertFalse(updated["data"]["enabled"])
        self.assertEqual(9, updated["data"]["page_size"])

        delete_resp = self.client.delete(f"/api/sources/wechat/{created_account['id']}")
        self.assertEqual(200, delete_resp.status_code)
        self.assertTrue(delete_resp.get_json()["success"])

        final_resp = self.client.get("/api/sources/wechat")
        self.assertGreaterEqual(len(final_resp.get_json()["data"]), 1)


if __name__ == "__main__":
    unittest.main()
