from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional

from models.article_record import ArticleRecord
from models.bid_record import BidRecord
from storage.file_storage import FileStorage
from utils.config_loader import load_config
from utils.logger import setup_logger


class DataManager:
    """Provide persistence, deduplication, and query helpers for articles and bids."""

    def __init__(
        self,
        config_file: str = "config.yml",
        *,
        config: Optional[Mapping[str, Any]] = None,
        db_session_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.config_path = Path(config_file)
        self.config = dict(config) if config else load_config(self.config_path)

        base_dir = self.config_path.parent
        paths_cfg = self.config["paths"]

        self.data_dir = self._resolve_path(paths_cfg["data_dir"], base=base_dir)
        self.log_dir = self._resolve_path(paths_cfg.get("log_dir", "data/logs"), base=base_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.articles_file = self.data_dir / "articles.json"
        self.bids_file = self.data_dir / "bids.json"

        self.logger = setup_logger(self.__class__.__name__, log_dir=self.log_dir)
        self.storage = FileStorage(logger=self.logger)
        self.db_session_factory = db_session_factory
        self.use_db = bool(self.db_session_factory)

    def save_bids(self, bids: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        """Persist bids to disk, returning only the newly added entries."""
        if self.use_db:
            return self._save_bids_db(bids)

        existing_bids = self.storage.load_json(self.bids_file)
        existing_ids = {bid.get("id") for bid in existing_bids if bid.get("id")}

        new_bids: List[Dict[str, Any]] = []
        for bid in bids:
            bid_id = bid.get("id")
            if not bid_id or bid_id in existing_ids:
                continue
            bid_record = self._with_defaults(bid)
            existing_bids.append(bid_record)
            existing_ids.add(bid_id)
            new_bids.append(bid_record)

        if new_bids:
            self.storage.save_json(self.bids_file, existing_bids)
            self.logger.info("Saved %d new bid(s).", len(new_bids))

        return new_bids

    def get_all_bids(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return all bids, optionally filtering by status."""
        if self.use_db:
            session = self._session()
            try:
                query = session.query(BidRecord)
                if status:
                    query = query.filter(BidRecord.status == status)
                records = query.order_by(BidRecord.extracted_time.desc()).all()
                return [record.to_dict() for record in records]
            finally:
                session.close()

        bids = self.storage.load_json(self.bids_file)
        if status:
            bids = [bid for bid in bids if bid.get("status") == status]
        bids.sort(key=lambda b: b.get("extracted_time", ""), reverse=True)
        return bids

    def update_bid_status(self, bid_id: str, new_status: str) -> bool:
        """Update a bid's status."""
        if self.use_db:
            session = self._session()
            try:
                record = session.get(BidRecord, bid_id)
                if not record:
                    return False
                record.status = new_status
                record.updated_time = self._timestamp()
                session.commit()
                self.logger.info("Updated bid %s status -> %s", bid_id, new_status)
                return True
            except Exception as exc:
                session.rollback()
                self.logger.error("Failed to update bid %s: %s", bid_id, exc)
                return False
            finally:
                session.close()

        bids = self.storage.load_json(self.bids_file)
        updated = False
        for bid in bids:
            if bid.get("id") == bid_id:
                bid["status"] = new_status
                bid["updated_time"] = self._timestamp()
                updated = True
                break

        if updated:
            self.storage.save_json(self.bids_file, bids)
            self.logger.info("Updated bid %s status -> %s", bid_id, new_status)
        return updated

    def is_article_crawled(self, url: str) -> bool:
        """Return True when the URL already exists in stored articles."""
        if not url:
            return False

        if self.use_db:
            session = self._session()
            try:
                exists = (
                    session.query(ArticleRecord.id)
                    .filter(ArticleRecord.url == url)
                    .first()
                )
                return exists is not None
            finally:
                session.close()

        articles = self.storage.load_json(self.articles_file)
        return any(article.get("url") == url for article in articles)

    def save_article(self, article_data: Mapping[str, Any]) -> bool:
        """Persist article metadata if not already recorded."""
        url = str(article_data.get("url", "")).strip()
        if not url:
            self.logger.warning("Cannot save article without URL.")
            return False
        record = {
            "url": url,
            "title": article_data.get("title", ""),
            "author": article_data.get("author", ""),
            "publish_time": article_data.get("publish_time", ""),
            "digest": article_data.get("digest", ""),
            "crawled_time": self._timestamp(),
            "has_bid_info": article_data.get("has_bid_info", False),
            "bid_count": article_data.get("bid_count", 0),
        }

        if self.use_db:
            session = self._session()
            try:
                exists = (
                    session.query(ArticleRecord.id)
                    .filter(ArticleRecord.url == url)
                    .first()
                )
                if exists:
                    return False
                session.add(ArticleRecord.from_mapping(record))
                session.commit()
                self.logger.info("Saved article meta: %s", url)
                return True
            except Exception as exc:
                session.rollback()
                self.logger.error("Failed to save article %s: %s", url, exc)
                return False
            finally:
                session.close()

        articles = self.storage.load_json(self.articles_file)
        if any(article.get("url") == url for article in articles):
            return False

        articles.append(record)
        saved = self.storage.save_json(self.articles_file, articles)
        if saved:
            self.logger.info("Saved article meta: %s", url)
        return saved

    def get_all_articles(self) -> List[Dict[str, Any]]:
        """Return stored article metadata."""
        if self.use_db:
            session = self._session()
            try:
                records = session.query(ArticleRecord).order_by(ArticleRecord.id.desc()).all()
                return [record.to_dict() for record in records]
            finally:
                session.close()

        return self.storage.load_json(self.articles_file)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate counts for articles and bids."""
        if self.use_db:
            session = self._session()
            try:
                total_articles = session.query(ArticleRecord).count()
                total_bids = session.query(BidRecord).count()
                new_bids = session.query(BidRecord).filter(BidRecord.status == "new").count()
                notified_bids = (
                    session.query(BidRecord).filter(BidRecord.status == "notified").count()
                )
                archived_bids = (
                    session.query(BidRecord).filter(BidRecord.status == "archived").count()
                )
                return {
                    "total_articles": total_articles,
                    "total_bids": total_bids,
                    "new_bids": new_bids,
                    "notified_bids": notified_bids,
                    "archived_bids": archived_bids,
                }
            finally:
                session.close()

        articles = self.get_all_articles()
        bids = self.storage.load_json(self.bids_file)
        stats = {
            "total_articles": len(articles),
            "total_bids": len(bids),
            "new_bids": 0,
            "notified_bids": 0,
            "archived_bids": 0,
        }
        for bid in bids:
            status = bid.get("status")
            if status == "new":
                stats["new_bids"] += 1
            elif status == "notified":
                stats["notified_bids"] += 1
            elif status == "archived":
                stats["archived_bids"] += 1
        return stats

    def reset_data(self) -> bool:
        """Clear all article and bid data from storage (DB or file)."""
        if self.use_db:
            session = self._session()
            try:
                # Delete bids first due to foreign key constraints if any (though currently loose)
                session.query(BidRecord).delete()
                session.query(ArticleRecord).delete()
                session.commit()
                self.logger.warning("All data cleared from database.")
                return True
            except Exception as exc:
                session.rollback()
                self.logger.error("Failed to clear database: %s", exc)
                return False
            finally:
                session.close()

        # File mode
        try:
            self.storage.save_json(self.articles_file, [])
            self.storage.save_json(self.bids_file, [])
            self.logger.warning("All data cleared from JSON files.")
            return True
        except Exception as exc:
            self.logger.error("Failed to clear JSON files: %s", exc)
            return False

    @staticmethod
    def _with_defaults(bid: Mapping[str, Any]) -> Dict[str, Any]:
        record = dict(bid)
        record.setdefault("status", "new")
        record.setdefault("extracted_time", DataManager._timestamp())
        return record

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _resolve_path(path_value: str, *, base: Path) -> Path:
        path = Path(path_value)
        if not path.is_absolute():
            path = (base / path).resolve()
        return path

    def _session(self):
        if not self.db_session_factory:
            raise RuntimeError("Database session factory is not configured.")
        return self.db_session_factory()

    def _save_bids_db(self, bids: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        session = self._session()
        new_records: List[BidRecord] = []
        try:
            for bid in bids:
                bid_id = bid.get("id")
                if not bid_id:
                    continue
                if session.get(BidRecord, bid_id):
                    continue
                payload = self._with_defaults(bid)
                record = BidRecord.from_mapping(payload)
                session.add(record)
                new_records.append(record)
            if new_records:
                session.commit()
                self.logger.info("Saved %d new bid(s) to database.", len(new_records))
            else:
                session.rollback()
            return [record.to_dict() for record in new_records]
        except Exception as exc:
            session.rollback()
            self.logger.error("Failed to save bids to database: %s", exc)
            return []
        finally:
            session.close()
