"""Flask web application entry point for the bid crawler system."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, MutableMapping, Optional

from flask import Flask, jsonify, render_template, request, session, g, redirect, url_for

from sqlalchemy import text

from core.article_fetcher import SougouWeChatFetcher
from core.bid_extractor import BidInfoExtractor
from core.data_manager import DataManager
from core.database import init_db
from core.notification import EmailNotificationService
from core.scheduler import CrawlScheduler, SchedulerConfig
from core.scraper import WeChatArticleScraper
from utils.config_loader import load_config, dump_config, read_config_file
from utils.logger import setup_logger
from utils.config_migrator import _generate_account_id
from models.wechat_account import WeChatAccount
from core.auth_manager import AuthManager
from models.user import User

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
        db_session_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.config = config
        self.data_manager = data_manager
        self.fetcher = fetcher
        self.scraper = scraper
        self.extractor = extractor
        self.notifier = notifier
        self.logger = logger
        self.db_session_factory = db_session_factory

    def run(self, status: StatusDict, update_status: StatusUpdater) -> None:
        """Execute the crawl pipeline and update the shared status dict."""
        update_status(message="正在获取文章列表...", progress=0, total=0, last_error=None)

        # Import here to avoid circular dependency
        from core.multi_source_crawler import MultiSourceCrawler
        
        max_articles = self.config.get("wechat", {}).get("max_articles_per_crawl", 50)
        
        # Use multi-source crawler to fetch from all enabled accounts
        multi_crawler = MultiSourceCrawler(
            self.config,
            logger=self.logger,
            session_factory=self.db_session_factory,
        )
        article_list = multi_crawler.fetch_all_articles(max_articles=max_articles)
        
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
            message=f"共发现 {len(article_list)} 篇文章,其中 {len(new_articles)} 篇未爬取。",
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
            update_status(message="文章抓取完成,但未获取到内容。")
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
                message=f"爬取完成,新增 {len(all_new_bids)} 条招标信息。",
                progress=len(article_urls),
                total=len(article_urls),
            )
        else:
            update_status(message="爬取完成,本次未发现新的招标信息。")


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
    config_path: str | Path = "config.yml",
    config: Optional[Mapping[str, Any]] = None,
    data_manager: Optional[DataManager] = None,
    fetcher: Optional[SougouWeChatFetcher] = None,
    scraper: Optional[WeChatArticleScraper] = None,
    extractor: Optional[BidInfoExtractor] = None,
    notifier: Optional[EmailNotificationService] = None,
    crawl_runner: Optional[CrawlRunner] = None,
    controller_executor: Optional[Executor] = None,
    # Dependency Injection for testing
    db_session_factory: Optional[Callable[[], Any]] = None,
    auth_manager: Optional[AuthManager] = None,
) -> Flask:
    """Application factory so tests can inject mocked dependencies."""
    config_path = Path(config_path)
    config_data = dict(config) if config else _load_config(config_path)
    paths_cfg = config_data.get("paths", {})
    log_dir = Path(paths_cfg.get("log_dir", "data/logs"))
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logger("WebApp", log_dir=log_dir)

    db = init_db(config_data)
    
    # Check if DB is configured and working
    db_ready = False
    try:
        if db.test_connection():
            db.create_tables()
            db_ready = True
            logger.info("Database connection verified.")
        else:
            logger.warning("Database connection failed. Entering setup mode.")
    except Exception as e:
        logger.warning(f"Database init failed: {e}. Entering setup mode.")

    db_session_factory = db_session_factory or db.get_session_factory()
    
    # Only seed if DB is ready
    if db_ready:
        seed_path = _find_seed_sql()
        _apply_seed_sql(db_session_factory, seed_path, logger)

    app = Flask(
        __name__,
        template_folder="web/templates",
        static_folder="web/static",
    )

    app.config["DB_READY"] = db_ready
    app.secret_key = config_data.get("secret_key", "dev-secret-key-change-in-prod")
    
    auth_manager = auth_manager or AuthManager(db_session_factory)

    @app.before_request
    def load_logged_in_user():
        auth_manager.load_logged_in_user()

    @app.before_request
    def check_setup_and_auth():
        # 1. Setup check
        if not app.config.get("DB_READY"):
            if request.path.startswith("/static") or request.path.startswith("/api/setup") or request.path == "/setup":
                return
            return redirect("/setup")
            
        # 2. Auth check
        public_endpoints = [
            "/login", 
            "/setup", 
            "/static", 
            "/api/login",
            "/api/setup"
        ]
        if any(request.path.startswith(p) for p in public_endpoints):
            return

        if g.user is None:
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "message": "Unauthorized"}), 401
            return redirect("/login")

    @app.route("/setup")
    def setup_page():
        if app.config.get("DB_READY"):
            return redirect("/dashboard")
        
        current_cfg = {}
        try:
            current_cfg = _load_config(config_path).get("database", {})
        except:
            pass
            
        return render_template("setup.html", db_config=current_cfg)

    @app.route("/login")
    def login_page():
        if g.user:
            return redirect("/dashboard")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        auth_manager.logout()
        return redirect("/login")

    @app.post("/api/login")
    def api_login():
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data"}), 400
        
        if auth_manager.login(data.get("username"), data.get("password")):
            return jsonify({"success": True})
        
        return jsonify({"success": False, "message": "用户名或密码错误"}), 401

    @app.post("/api/change-password")
    def api_change_password():
        if not g.user:
            return jsonify({"success": False, "message": "Unauthorized"}), 401
            
        data = request.get_json()
        old = data.get("old_password")
        new = data.get("new_password")
        
        if auth_manager.change_password(g.user["id"], old, new):
            return jsonify({"success": True})
        
        return jsonify({"success": False, "message": "原密码错误"}), 400

    @app.post("/api/setup/test-db")
    def test_db_connection():
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "无效数据"}), 400
        
        # Construct temporary config
        temp_config = {
            "database": {
                "host": data.get("host"),
                "port": data.get("port"),
                "name": data.get("name"),
                "user": data.get("user"),
                "password": data.get("password"),
            }
        }
        
        # Use a temporary Database instance to test
        from core.database import Database
        try:
            temp_db = Database(temp_config)
            # Directly check connection to capture specific error
            with temp_db.get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            return jsonify({"success": True, "message": "连接成功"})
        except Exception as e:
            # Return specific error message (e.g. password failed)
            logger.error(f"DB Test Connection failed: {e}")
            return jsonify({"success": False, "message": str(e)}), 400

    @app.post("/api/setup/save")
    def save_setup():
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "无效数据"}), 400
            
        try:
            # Load current config
            current = _load_config(config_path)
            
            # Update database section
            if "database" not in current:
                current["database"] = {}
            
            db_cfg = data.get("database", {})
            
            # Ensure port is int
            port_val = db_cfg.get("port")
            try:
                port_val = int(port_val) if port_val else 5432
            except (ValueError, TypeError):
                port_val = 5432

            current["database"].update({
                "host": db_cfg.get("host"),
                "port": port_val,
                "name": db_cfg.get("name"),
                "user": db_cfg.get("user"),
                "password": db_cfg.get("password"),
                "url": None 
            })
            
            # Debug log
            logger.info(f"Applying new database config: host={db_cfg.get('host')}, port={port_val}, user={db_cfg.get('user')}, db={db_cfg.get('name')}")
            
            # Save to custom.yml
            exe_dir = Path(config_path).parent if config_path else Path.cwd()
            custom_path = exe_dir / "custom.yml"
            dump_config(custom_path, current)
            
            # Reload global DB
            if db.reload_config(current):
                db.create_tables()
                
                # Create Admin User if provided
                admin_cfg = data.get("admin", {})
                if admin_cfg and admin_cfg.get("username") and admin_cfg.get("password"):
                    session = db.get_session()
                    try:
                        User.create_admin(session, admin_cfg["username"], admin_cfg["password"])
                    except Exception as e:
                        logger.error(f"Failed to create admin user: {e}")
                    finally:
                        session.close()

                # Apply seed if needed
                _apply_seed_sql(db.get_session_factory(), _find_seed_sql(), logger)
                
                app.config["DB_READY"] = True
                return jsonify({"success": True, "message": "配置保存成功"})
            else:
                logger.error("Failed to reload DB config after save.")
                return jsonify({"success": False, "message": "保存后连接失败"}), 500
                
        except Exception as e:
            logger.error(f"Setup save failed: {e}", exc_info=True)
            return jsonify({"success": False, "message": str(e)}), 500

    data_manager = data_manager or DataManager(
        str(config_path),
        config=config_data,
        db_session_factory=db_session_factory,
    )
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
        db_session_factory=db_session_factory,
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
            "DB_SESSION_FACTORY": db_session_factory,
        }
    )

    def _db_session():
        factory = app.config.get("DB_SESSION_FACTORY")
        return factory() if factory else None

    @app.route("/")
    def index():
        from flask import redirect
        return redirect("/dashboard")

    @app.route("/dashboard")
    def dashboard():
        return render_template("dashboard.html")

    @app.route("/bidding-hall")
    def bidding_hall():
        return render_template("bidding_hall.html")

    @app.route("/sources")
    def sources():
        return render_template("sources.html")

    @app.route("/settings")
    def settings():
        return render_template("settings.html")

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

    @app.get("/api/config")
    def get_config():
        """Return current custom config for editing."""
        custom_path = Path("custom.yml")
        exe_dir = Path(config_path).parent if config_path else Path.cwd()
        legacy_path = custom_path.with_suffix(".json")
        custom_candidates = [
            custom_path,
            exe_dir / "custom.yml",
            legacy_path,
            exe_dir / "custom.json",
        ]
        
        for candidate in custom_candidates:
            if candidate.exists():
                try:
                    custom_cfg = read_config_file(candidate)
                    return jsonify({"success": True, "data": custom_cfg})
                except Exception as exc:
                    logger.warning("Failed to read %s: %s", candidate, exc)
        
        # Return empty structure if no custom.yml found
        return jsonify({"success": True, "data": {
            "wechat": {},
            "email": {},
            "scheduler": {}
        }})

    @app.post("/api/config")
    def save_config():
        """Save configuration to custom.yml and reload."""
        try:
            new_config = request.get_json()
            if not new_config:
                return jsonify({"success": False, "message": "无效的配置数据"}), 400
            
            # Load existing to merge
            current = _load_config(config_path)
            
            # Deep merge specific sections to avoid wiping other fields (like fakeid/token if they were global)
            # Though UI sends full sections, we should be careful.
            
            # Wechat section
            if "wechat" in new_config:
                if "wechat" not in current:
                    current["wechat"] = {}
                # Update only known keys from UI
                current["wechat"]["days_limit"] = new_config["wechat"].get("days_limit")
                current["wechat"]["filter_keyword_logic"] = new_config["wechat"].get("filter_keyword_logic")
                current["wechat"]["keyword_filters"] = new_config["wechat"].get("keyword_filters")
                current["wechat"]["filter_keywords"] = new_config["wechat"].get("filter_keywords")

            # Email section
            if "email" in new_config:
                current["email"] = new_config["email"]
                
            # Scheduler
            if "scheduler" in new_config:
                current["scheduler"] = new_config["scheduler"]

            # Save to custom.yml next to the executable
            exe_dir = Path(config_path).parent if config_path else Path.cwd()
            custom_path = exe_dir / "custom.yml"
            
            dump_config(custom_path, current)
            
            # Hot reload: update in-memory config
            _reload_service_configs(current)
            
            logger.info("Configuration saved and reloaded from web UI")
            return jsonify({"success": True, "message": "配置已保存并生效"})
            
        except Exception as exc:
            logger.error("Failed to save config: %s", exc, exc_info=True)
            return jsonify({"success": False, "message": f"保存失败: {str(exc)}"}), 500

    def _reload_service_configs(new_config: Mapping[str, Any]) -> None:
        """Update in-memory configurations with new settings."""
        reloaded = _load_config(config_path)
        controller = app.config["CRAWL_CONTROLLER"]
        controller.runner.config = reloaded

        fetcher = controller.runner.fetcher
        wechat_cfg = reloaded.get("wechat", {})
        fetcher.config = reloaded
        fetcher.fakeid = str(wechat_cfg.get("fakeid", "")).strip()
        fetcher.token = str(wechat_cfg.get("token", "")).strip()
        fetcher.cookie = str(wechat_cfg.get("cookie", "")).strip()
        fetcher.page_size = max(1, int(wechat_cfg.get("page_size", 5) or 5))
        fetcher.days_limit = int(wechat_cfg.get("days_limit", 7) or 0)

        old_scheduler = app.config["CRAWL_SCHEDULER"]
        old_scheduler.stop()

        new_scheduler_cfg = _build_scheduler_config(reloaded.get("scheduler", {}))
        new_scheduler = CrawlScheduler(controller, new_scheduler_cfg, logger=logger)
        new_scheduler.start()
        app.config["CRAWL_SCHEDULER"] = new_scheduler

    # Resource Management APIs
    @app.get("/api/sources/wechat")
    def get_wechat_accounts():
        """List all WeChat accounts."""
        session = _db_session()
        try:
            accounts = WeChatAccount.get_all(session)
            data = [account.to_dict() for account in accounts]
        finally:
            session.close()
        return jsonify({"success": True, "data": data})
    
    @app.post("/api/sources/wechat")
    def create_wechat_account():
        """Add a new WeChat account."""
        try:
            account = request.get_json()
            if not account or not account.get("name"):
                return jsonify({"success": False, "message": "账号名称不能为空"}), 400
            
            session = _db_session()
            try:
                if not account.get("id"):
                    account["id"] = _generate_account_id(account["name"])
                if WeChatAccount.get_by_id(session, account["id"]):
                    return jsonify({"success": False, "message": "账号ID已存在"}), 400
                
                # Validate credentials
                temp_config = {
                    "wechat": {
                        "fakeid": account.get("fakeid"),
                        "token": account.get("token"),
                        "cookie": account.get("cookie"),
                    }
                }
                fetcher = SougouWeChatFetcher(config=temp_config)
                is_valid, error_msg = fetcher.validate_credentials()
                if not is_valid:
                    return jsonify({"success": False, "message": error_msg}), 400

                created = WeChatAccount.create(session, account)
                payload = created.to_dict()
            finally:
                session.close()
            return jsonify({"success": True, "data": payload})
        except Exception as exc:
            logger.error("Failed to create account: %s", exc, exc_info=True)
            return jsonify({"success": False, "message": str(exc)}), 500
    
    @app.put("/api/sources/wechat/<account_id>")
    def update_wechat_account(account_id):
        """Update an existing WeChat account."""
        try:
            updated_account = request.get_json()
            if not updated_account:
                return jsonify({"success": False, "message": "无效数据"}), 400

            session = _db_session()
            try:
                # Check if account exists first
                existing = WeChatAccount.get_by_id(session, account_id)
                if not existing:
                    return jsonify({"success": False, "message": "账号不存在"}), 404

                # Validate credentials if they are being updated
                # We merge with existing data to ensure we have a full set for validation if partial update
                merged_data = existing.to_dict()
                merged_data.update(updated_account)
                
                temp_config = {
                    "wechat": {
                        "fakeid": merged_data.get("fakeid"),
                        "token": merged_data.get("token"),
                        "cookie": merged_data.get("cookie"),
                    }
                }
                fetcher = SougouWeChatFetcher(config=temp_config)
                is_valid, error_msg = fetcher.validate_credentials()
                if not is_valid:
                    return jsonify({"success": False, "message": error_msg}), 400

                updated = WeChatAccount.update(session, account_id, updated_account)
                if not updated:
                    return jsonify({"success": False, "message": "账号不存在"}), 404
                payload = updated.to_dict()
            finally:
                session.close()
            return jsonify({"success": True, "data": payload})
        except Exception as exc:
            logger.error("Failed to update account: %s", exc, exc_info=True)
            return jsonify({"success": False, "message": str(exc)}), 500
    
    @app.delete("/api/sources/wechat/<account_id>")
    def delete_wechat_account(account_id):
        """Delete a WeChat account."""
        try:
            session = _db_session()
            try:
                deleted = WeChatAccount.delete(session, account_id)
            finally:
                session.close()
            if not deleted:
                return jsonify({"success": False, "message": "账号不存在"}), 404
            return jsonify({"success": True, "message": "已删除"})
        except Exception as exc:
            logger.error("Failed to delete account: %s", exc, exc_info=True)
            return jsonify({"success": False, "message": str(exc)}), 500

    @app.post("/api/admin/reset")
    def reset_system_data():
        """Clear all historical data (articles and bids)."""
        try:
            success = data_manager.reset_data()
            if success:
                return jsonify({"success": True, "message": "所有历史数据已清空"})
            else:
                return jsonify({"success": False, "message": "数据清空失败"}), 500
        except Exception as exc:
            logger.error("Failed to reset data: %s", exc, exc_info=True)
            return jsonify({"success": False, "message": str(exc)}), 500

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





def _find_seed_sql() -> Optional[Path]:
    """Locate the bundled seed SQL file."""
    candidates = [
        Path("db/seed.sql"),
        Path(__file__).resolve().parent / "db/seed.sql",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def _apply_seed_sql(session_factory, sql_path: Optional[Path], logger) -> None:
    """Apply seed SQL to populate default accounts if database is empty."""
    if not session_factory or not sql_path or not sql_path.exists():
        return
    session = session_factory()
    try:
        has_records = session.query(WeChatAccount).count()
        if has_records:
            return
        sql_text = sql_path.read_text(encoding="utf-8")
        session.execute(text(sql_text))
        session.commit()
        if logger:
            logger.info("Database seeded using %s", sql_path)
    except Exception as exc:
        session.rollback()
        if logger:
            logger.error("Failed to apply seed SQL %s: %s", sql_path, exc)
    finally:
        session.close()


if __name__ == "__main__":  # pragma: no cover
    application = create_app()
    application.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
