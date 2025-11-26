import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core.notification import EmailNotificationService, SMTPConfigurationError


class DummySMTP:
    """Fake SMTP client capturing operations for assertions."""

    instance = None

    def __init__(self, host, port, timeout=30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.ehlo_called = 0
        self.starttls_called = False
        self.login_calls = []
        self.sent_messages = []
        self.closed = False
        DummySMTP.instance = self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.closed = True
        return False

    def ehlo(self):
        self.ehlo_called += 1

    def starttls(self):
        self.starttls_called = True

    def login(self, username, password):
        self.login_calls.append((username, password))

    def send_message(self, message):
        self.sent_messages.append(message)


class DummyDataManager:
    def __init__(self):
        self.updated = []

    def update_bid_status(self, bid_id, status):
        self.updated.append((bid_id, status))
        return True


class TestEmailNotificationService(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        log_dir = Path(self.tmpdir.name) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.config = {
            "email": {
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "sender_email": "bot@example.com",
                "sender_password": "secret",
                "recipient_emails": ["alice@example.com", "bob@example.com"],
            },
            "paths": {
                "log_dir": str(log_dir),
            },
        }
        self.logger = mock.MagicMock()

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_missing_config_raises_error(self) -> None:
        broken_config = {
            "email": {},
            "paths": {"log_dir": str(Path(self.tmpdir.name) / "logs2")},
        }
        with self.assertRaises(SMTPConfigurationError):
            EmailNotificationService(config=broken_config, logger=self.logger)

    def test_format_email_body_contains_key_fields(self) -> None:
        service = EmailNotificationService(
            config=self.config,
            logger=self.logger,
            smtp_class=DummySMTP,
        )
        html = service._format_email_body(
            [
                {
                    "project_name": "测试项目",
                    "budget": "50万元",
                    "purchaser": "采购单位",
                    "doc_time": "2025-11-25",
                    "project_number": "ABC-123",
                    "service_period": "1年",
                    "content": "采购内容描述",
                    "source_url": "https://example.com/bid",
                    "source_title": "查看原文",
                }
            ]
        )
        self.assertIn("测试项目", html)
        self.assertIn("50万元", html)
        self.assertIn("https://example.com/bid", html)

    def test_send_bid_notification_updates_status_and_sends_email(self) -> None:
        service = EmailNotificationService(
            config=self.config,
            logger=self.logger,
            smtp_class=DummySMTP,
        )
        bids = [
            {
                "id": "bid-1",
                "project_name": "测试项目1",
                "budget": "80万元",
                "purchaser": "采购单位",
                "doc_time": "2025-11-25",
                "source_url": "https://example.com/1",
                "source_title": "原文1",
            }
        ]
        manager = DummyDataManager()

        result = service.send_bid_notification(bids, data_manager=manager)

        self.assertTrue(result)
        self.assertEqual([("bid-1", "notified")], manager.updated)
        smtp_instance = DummySMTP.instance
        self.assertIsNotNone(smtp_instance)
        self.assertTrue(smtp_instance.starttls_called)
        self.assertEqual(("bot@example.com", "secret"), smtp_instance.login_calls[0])
        self.assertEqual(1, len(smtp_instance.sent_messages))
        msg = smtp_instance.sent_messages[0]
        html_part = None
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html_part = part.get_payload(decode=True).decode("utf-8")
                break
        self.assertIsNotNone(html_part)
        self.assertIn("测试项目1", html_part)


if __name__ == "__main__":
    unittest.main()
