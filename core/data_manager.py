from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from storage.file_storage import FileStorage
from utils.config_loader import load_config
from utils.logger import setup_logger


class DataManager:
    """Provide persistence, deduplication, and query helpers for articles and bids."""

    def __init__(self, config_file: str = "config.json") -> None:
        self.config_path = Path(config_file)
        self.config = load_config(self.config_path)

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

    def save_bids(self, bids: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        """Persist bids to disk, returning only the newly added entries."""
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
        bids = self.storage.load_json(self.bids_file)
        if status:
            bids = [bid for bid in bids if bid.get("status") == status]
        bids.sort(key=lambda b: b.get("extracted_time", ""), reverse=True)
        return bids

    def update_bid_status(self, bid_id: str, new_status: str) -> bool:
        """Update a bid's status."""
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
        articles = self.storage.load_json(self.articles_file)
        return any(article.get("url") == url for article in articles)

    def save_article(self, article_data: Mapping[str, Any]) -> bool:
        """Persist article metadata if not already recorded."""
        url = str(article_data.get("url", "")).strip()
        if not url:
            self.logger.warning("Cannot save article without URL.")
            return False

        articles = self.storage.load_json(self.articles_file)
        if any(article.get("url") == url for article in articles):
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
        articles.append(record)
        saved = self.storage.save_json(self.articles_file, articles)
        if saved:
            self.logger.info("Saved article meta: %s", url)
        return saved

    def get_all_articles(self) -> List[Dict[str, Any]]:
        """Return stored article metadata."""
        return self.storage.load_json(self.articles_file)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate counts for articles and bids."""
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
