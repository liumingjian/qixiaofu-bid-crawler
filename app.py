"""Flask web application entry point for the bid crawler system."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, MutableMapping, Optional

from flask import Flask, jsonify, render_template, request

from core.article_fetcher import SougouWeChatFetcher
from core.bid_extractor import BidInfoExtractor
from core.data_manager import DataManager
from core.notification import EmailNotificationService
from core.scheduler import CrawlScheduler, SchedulerConfig
from core.scraper import WeChatArticleScraper
from utils.config_loader import load_config
from utils.logger import setup_logger

StatusDict = MutableMapping[str, Any]
StatusUpdater = Callable[..., None]
Executor = Callable[[Callable[[], None]], Any]


def _load_config(path: Path) -> Dict[str, Any]:
    return load_config(path)


class CrawlRunner:
    """Encapsulate the full crawl workflow so it can be triggered from the web layer."""

    def __init__(
        self,
        config: Mapping[str, Any],
        *,
        data_manager: DataManager,
        fetcher: SougouWeChatFetcher,
        scraper: WeChatArticleScraper,
        extractor: BidInfoExtractor,
        notifier: EmailNotificationService,
        logger,
    ) -> None:
        self.config = config
        self.data_manager = data_manager
        self.fetcher = fetcher
        self.scraper = scraper
        self.extractor = extractor
        self.notifier = notifier
        self.logger = logger

    def run(self, status: StatusDict, update_status: StatusUpdater) -> None:
        """Execute the crawl pipeline and update the shared status dict."""
        update_status(message="正在获取文章列表...", progress=0, total=0, last_error=None)

        max_articles = self.config.get("wechat", {}).get("max_articles_per_crawl", 50)
        article_list = self.fetcher.fetch_article_list(max_articles=max_articles)
        if not article_list:
            update_status(message="未获取到文章列表", total=0)
            return

        new_articles = []
        seen_urls = set()
        for article in article_list:
            url = str(article.get("url", "")).strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            if not self.data_manager.is_article_crawled(url):
                new_articles.append(article)

        update_status(
            total=len(new_articles),
            message=f"共发现 {len(article_list)} 篇文章，其中 {len(new_articles)} 篇未爬取。",
        )
        if not new_articles:
            return

        article_urls = [article["url"] for article in new_articles]
        update_status(message="正在批量爬取文章内容...", progress=0)

        def progress_callback(index: int, total: int, article_data: Optional[Mapping[str, Any]]):
            title = (article_data or {}).get("title", "")
            truncated = title[:30]
            update_status(progress=index, total=total, message=f"正在爬取: {truncated}...")

        articles_data = self.scraper.scrape_articles_batch(article_urls, callback=progress_callback)
        articles_data = [article for article in articles_data if article]
        if not articles_data:
            update_status(message="文章抓取完成，但未获取到内容。")
            return

        update_status(message="正在提取招标信息...")
        all_new_bids = []
        for article_data in articles_data:
            content_text = article_data.get("content_text", "")
            bids = self.extractor.extract_from_text(content_text, article_data)
            if bids:
                new_bids = self.data_manager.save_bids(bids)
                all_new_bids.extend(new_bids)
            self.data_manager.save_article(article_data)

        if all_new_bids:
            update_status(message=f"正在发送邮件通知 ({len(all_new_bids)} 条)...")
            self.notifier.send_bid_notification(all_new_bids, self.data_manager)
            update_status(
                message=f"爬取完成，新增 {len(all_new_bids)} 条招标信息。",
                progress=len(article_urls),
                total=len(article_urls),
            )
        else:
            update_status(message="爬取完成，本次未发现新的招标信息。")


class CrawlController:
    """Manage crawl runner execution and expose status helpers."""

    def __init__(
        self,
        runner: CrawlRunner,
        *,
        status: Optional[StatusDict] = None,
        logger=None,
        executor: Optional[Executor] = None,
    ) -> None:
        self.runner = runner
        self.logger = logger
        self.status: StatusDict = status or {
            "is_running": False,
            "progress": 0,
            "total": 0,
            "message": "等待任务",
            "last_error": None,
        }
        self.lock = threading.Lock()
        self.executor = executor or self._default_executor

    def start(self) -> bool:
        """Attempt to start the crawl task in the background."""
        with self.lock:
            if self.status.get("is_running"):
                return False
            self.status.update(
                {
                    "is_running": True,
                    "progress": 0,
                    "total": 0,
                    "message": "爬取任务初始化...",
                    "last_error": None,
                }
            )

        def task():
            try:
                self.runner.run(self.status, self._update_status)
            except Exception as exc:  # pragma: no cover - defensive logging
                if self.logger:
                    self.logger.error("Crawl task crashed: %s", exc, exc_info=True)
                self._update_status(message=f"爬取失败: {exc}", last_error=str(exc))
            finally:
                self._update_status(is_running=False)

        self.executor(task)
        return True

    def get_status(self) -> Dict[str, Any]:
        with self.lock:
            return dict(self.status)

    def _update_status(self, **kwargs):
        with self.lock:
            self.status.update(kwargs)

    @staticmethod
    def _default_executor(func: Callable[[], None]):
        thread = threading.Thread(target=func, daemon=True)
        thread.start()
        return thread


def create_app(
    *,
    config_path: str | Path = "config.json",
    config: Optional[Mapping[str, Any]] = None,
    data_manager: Optional[DataManager] = None,
    fetcher: Optional[SougouWeChatFetcher] = None,
    scraper: Optional[WeChatArticleScraper] = None,
    extractor: Optional[BidInfoExtractor] = None,
    notifier: Optional[EmailNotificationService] = None,
    crawl_runner: Optional[CrawlRunner] = None,
    controller_executor: Optional[Executor] = None,
) -> Flask:
    """Application factory so tests can inject mocked dependencies."""
    config_path = Path(config_path)
    config_data = dict(config) if config else _load_config(config_path)
    paths_cfg = config_data.get("paths", {})
    log_dir = Path(paths_cfg.get("log_dir", "data/logs"))
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logger("WebApp", log_dir=log_dir)

    app = Flask(
        __name__,
        template_folder="web/templates",
        static_folder="web/static",
    )

    data_manager = data_manager or DataManager(str(config_path))
    fetcher = fetcher or SougouWeChatFetcher(config_path=config_path)
    scraper = scraper or WeChatArticleScraper(config_path=config_path)
    extractor = extractor or BidInfoExtractor(logger=logger)
    notifier = notifier or EmailNotificationService(config_path=config_path, logger=logger)
    crawl_runner = crawl_runner or CrawlRunner(
        config_data,
        data_manager=data_manager,
        fetcher=fetcher,
        scraper=scraper,
        extractor=extractor,
        notifier=notifier,
        logger=logger,
    )

    controller = CrawlController(
        crawl_runner,
        logger=logger,
        executor=controller_executor,
    )

    scheduler_cfg = _build_scheduler_config(config_data.get("scheduler", {}))
    scheduler = CrawlScheduler(controller, scheduler_cfg, logger=logger)
    scheduler.start()

    app.config.update(
        {
            "CRAWL_CONTROLLER": controller,
            "DATA_MANAGER": data_manager,
            "LOGGER": logger,
            "CRAWL_SCHEDULER": scheduler,
        }
    )

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.get("/api/bids")
    def get_bids():
        status_filter = request.args.get("status")
        normalized = status_filter if status_filter and status_filter != "all" else None
        bids = data_manager.get_all_bids(normalized)
        return jsonify({"success": True, "data": bids, "count": len(bids)})

    @app.post("/api/crawl/start")
    def start_crawl():
        controller = app.config["CRAWL_CONTROLLER"]
        if not controller.start():
            return jsonify({"success": False, "message": "爬取任务已在运行中"}), 400
        return jsonify({"success": True, "message": "爬取任务已启动"})

    @app.get("/api/crawl/status")
    def crawl_status():
        controller = app.config["CRAWL_CONTROLLER"]
        return jsonify({"success": True, "data": controller.get_status()})

    @app.get("/api/stats")
    def stats():
        payload = data_manager.get_stats()
        return jsonify({"success": True, "data": payload})

    return app


def _build_scheduler_config(raw_cfg: Mapping[str, Any] | None) -> SchedulerConfig:
    if not raw_cfg:
        return SchedulerConfig()
    interval = raw_cfg.get("interval_minutes")
    try:
        interval_val = float(interval) if interval is not None else None
        if interval_val is not None and interval_val <= 0:
            interval_val = None
    except (TypeError, ValueError):
        interval_val = None
    return SchedulerConfig(
        enabled=bool(raw_cfg.get("enabled", False)),
        daily_time=str(raw_cfg.get("daily_time", "07:00")) if "daily_time" in raw_cfg else None,
        timezone=str(raw_cfg.get("timezone", "Asia/Shanghai")),
        cron=str(raw_cfg.get("cron", "")).strip() or None,
        interval_minutes=interval_val,
    )


if __name__ == "__main__":  # pragma: no cover
    application = create_app()
    application.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
