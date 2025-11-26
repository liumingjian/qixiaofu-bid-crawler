"""Email notification service for bid updates."""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
from pathlib import Path
from typing import Iterable, List, Mapping, MutableMapping, Optional, Sequence

from utils.config_loader import load_config
from utils.logger import setup_logger

BidRecord = Mapping[str, object]


class SMTPConfigurationError(ValueError):
    """Raised when the email configuration is incomplete."""


class EmailNotificationService:
    """Send HTML emails when new bids are available."""

    def __init__(
        self,
        config_path: str | Path = "config.yml",
        *,
        config: Optional[Mapping[str, object]] = None,
        logger=None,
        smtp_class=smtplib.SMTP,
        smtp_ssl_class=smtplib.SMTP_SSL,
    ) -> None:
        self.config_path = Path(config_path)
        self.config = dict(config) if config else self._load_config(self.config_path)

        email_cfg: MutableMapping[str, object] = dict(self.config.get("email", {}))
        paths_cfg = self.config.get("paths", {})

        base_dir = self.config_path.parent
        log_dir = self._resolve_path(paths_cfg.get("log_dir", "data/logs"), base=base_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        self.smtp_server: str = str(email_cfg.get("smtp_server", "")).strip()
        self.smtp_port: int = int(email_cfg.get("smtp_port", 0) or 0)
        self.sender_email: str = str(email_cfg.get("sender_email", "")).strip()
        self.sender_password: str = str(email_cfg.get("sender_password", "")).strip()
        recipients = email_cfg.get("recipient_emails", [])
        if isinstance(recipients, Sequence):
            self.recipient_emails = [str(item).strip() for item in recipients if str(item).strip()]
        else:
            self.recipient_emails = []
        self.smtp_timeout: int = int(email_cfg.get("timeout", 30) or 30)

        self.logger = logger or setup_logger(self.__class__.__name__, log_dir=log_dir)
        self.smtp_class = smtp_class
        self.smtp_ssl_class = smtp_ssl_class

        self._validate_config()

    def _load_config(self, path: Path) -> Mapping[str, object]:
        return load_config(path)

    def _validate_config(self) -> None:
        missing = []
        if not self.smtp_server:
            missing.append("email.smtp_server")
        if not self.smtp_port:
            missing.append("email.smtp_port")
        if not self.sender_email:
            missing.append("email.sender_email")
        if not self.sender_password:
            missing.append("email.sender_password")
        if not self.recipient_emails:
            missing.append("email.recipient_emails")
        if missing:
            raise SMTPConfigurationError(
                f"Email configuration missing required field(s): {', '.join(missing)}"
            )
        self.logger.info(
            "Email configuration validated. Recipients: %d", len(self.recipient_emails)
        )

    def send_bid_notification(
        self, bids: Sequence[BidRecord], data_manager=None
    ) -> bool:
        """Send an HTML summary of the provided bids."""
        bid_list = [dict(bid) for bid in bids if bid]
        if not bid_list:
            self.logger.info("No new bids to notify.")
            return True

        subject = f"发现 {len(bid_list)} 条新招标信息"
        body = self._format_email_body(bid_list)
        message = self._build_message(subject, body)

        try:
            self._send_email(message)
        except Exception as exc:  # pragma: no cover - logged and propagated as failure
            self.logger.error("Failed to send bid notification: %s", exc, exc_info=True)
            return False

        if data_manager:
            updated = 0
            for bid in bid_list:
                bid_id = str(bid.get("id") or "").strip()
                if not bid_id:
                    continue
                try:
                    if data_manager.update_bid_status(bid_id, "notified"):
                        updated += 1
                except Exception as exc:  # pragma: no cover - defensive logging
                    self.logger.error(
                        "Failed to update bid %s status to 'notified': %s", bid_id, exc
                    )
            if updated:
                self.logger.info("Updated %d bid(s) status to 'notified'.", updated)
        return True

    def send_test_email(self) -> bool:
        """Send a sample email to verify SMTP credentials."""
        sample_bid = {
            "id": "test-sample",
            "project_name": "测试招标项目",
            "budget": "100万元",
            "purchaser": "测试采购单位",
            "doc_time": "2025-11-25",
            "project_number": "TEST-001",
            "service_period": "1年",
            "content": "这是一封测试通知邮件，用于验证SMTP配置。",
            "source_url": "https://example.com",
            "source_title": "测试文章",
        }
        return self.send_bid_notification([sample_bid])

    def _build_message(self, subject: str, html_body: str) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = ", ".join(self.recipient_emails)
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        return msg

    def _send_email(self, msg: MIMEMultipart) -> None:
        if self.smtp_port == 465:
            smtp_cls = self.smtp_ssl_class
        else:
            smtp_cls = self.smtp_class

        with smtp_cls(self.smtp_server, self.smtp_port, timeout=self.smtp_timeout) as server:
            server.ehlo()
            if self.smtp_port == 587:
                server.starttls()
                server.ehlo()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
            self.logger.info(
                "Notification sent to %d recipient(s) via %s.",
                len(self.recipient_emails),
                self.smtp_server,
            )

    def _format_email_body(self, bids: Sequence[Mapping[str, object]]) -> str:
        """Return the HTML string for the email body."""
        body_parts: List[str] = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            '<meta charset="UTF-8" />',
            "<style>",
            "body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f6fb; margin: 0; padding: 0; }",
            ".wrapper { max-width: 820px; margin: 0 auto; padding: 20px; }",
            ".header { background: linear-gradient(135deg, #0076ff, #00c4ff); color: #fff; padding: 20px 30px; border-radius: 12px 12px 0 0; }",
            ".header h1 { margin: 0 0 6px; font-size: 22px; }",
            ".header p { margin: 0; font-size: 14px; }",
            ".bid-card { background: #fff; border-radius: 10px; padding: 18px 22px; box-shadow: 0 4px 14px rgba(15, 45, 86, 0.08); margin-top: 18px; }",
            ".bid-title { font-size: 18px; margin-bottom: 10px; color: #0f2d56; }",
            ".bid-field { margin: 6px 0; font-size: 14px; color: #39465f; }",
            ".bid-field span.label { font-weight: 600; color: #607087; display: inline-block; width: 110px; }",
            ".link-button { display: inline-block; margin-top: 12px; text-decoration: none; background-color: #0076ff; color: #fff; padding: 10px 18px; border-radius: 6px; font-weight: 600; }",
            ".link-button:hover { background-color: #005fcc; }",
            ".footer { text-align: center; color: #90a4c3; font-size: 12px; margin: 24px 0 10px; }",
            "@media only screen and (max-width: 600px) { .bid-card { padding: 16px; } .bid-field span.label { width: auto; display: block; } }",
            "</style>",
            "</head>",
            "<body>",
            '<div class="wrapper">',
            '<div class="header">',
            f"<h1>新招标信息通知</h1>",
            f"<p>发现 {len(bids)} 条新的招标信息，请及时查看。</p>",
            "</div>",
        ]

        for index, bid in enumerate(bids, 1):
            fields = self._format_bid_fields(bid)
            body_parts.extend(
                [
                    '<div class="bid-card">',
                    f'<div class="bid-title">{index}. {escape(str(bid.get("project_name") or "未命名项目"))}</div>',
                ]
                + fields
            )
            source_url = escape(str(bid.get("source_url") or "#"))
            source_title = escape(str(bid.get("source_title") or "查看原文"))
            body_parts.extend(
                [
                    f'<a class="link-button" href="{source_url}" target="_blank" rel="noopener">{source_title}</a>',
                    "</div>",
                ]
            )

        body_parts.extend(
            [
                '<div class="footer">此邮件由招标信息爬虫系统自动发送，如需停止接收，请联系管理员。</div>',
                "</div>",
                "</body>",
                "</html>",
            ]
        )
        return "\n".join(body_parts)

    def _format_bid_fields(self, bid: Mapping[str, object]) -> List[str]:
        field_order = [
            ("预算金额", bid.get("budget")),
            ("采购人", bid.get("purchaser")),
            ("获取文件时间", bid.get("doc_time")),
            ("项目编号", bid.get("project_number")),
            ("服务期限", bid.get("service_period")),
            ("采购内容", bid.get("content")),
        ]
        parts: List[str] = []
        for label, value in field_order:
            if value:
                parts.append(
                    f'<div class="bid-field"><span class="label">{label}：</span><span class="value">{escape(str(value))}</span></div>'
                )
        return parts

    @staticmethod
    def _resolve_path(value: str | Path, *, base: Path) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = (base / path).resolve()
        return path
