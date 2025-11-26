"""SQLAlchemy model for crawled WeChat articles."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, Integer, String, Text

from core.database import Base


class ArticleRecord(Base):
    """Persisted article metadata for deduplication and stats."""

    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(512), unique=True, nullable=False, index=True)
    title = Column(String(512), nullable=True)
    author = Column(String(128), nullable=True)
    publish_time = Column(String(64), nullable=True)
    digest = Column(Text, nullable=True)
    crawled_time = Column(String(64), nullable=False)
    has_bid_info = Column(Boolean, default=False)
    bid_count = Column(Integer, default=0)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title or "",
            "author": self.author or "",
            "publish_time": self.publish_time or "",
            "digest": self.digest or "",
            "crawled_time": self.crawled_time,
            "has_bid_info": bool(self.has_bid_info),
            "bid_count": self.bid_count or 0,
        }

    @classmethod
    def from_mapping(cls, payload: dict) -> "ArticleRecord":
        return cls(
            url=payload.get("url", ""),
            title=payload.get("title"),
            author=payload.get("author"),
            publish_time=payload.get("publish_time"),
            digest=payload.get("digest"),
            crawled_time=payload.get("crawled_time", ""),
            has_bid_info=bool(payload.get("has_bid_info", False)),
            bid_count=int(payload.get("bid_count", 0) or 0),
        )
