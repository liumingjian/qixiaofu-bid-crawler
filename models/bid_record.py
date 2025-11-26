"""SQLAlchemy model for extracted bid information."""

from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text

from core.database import Base


class BidRecord(Base):
    """Persisted bid entries."""

    __tablename__ = "bids"

    id = Column(String(64), primary_key=True)
    project_name = Column(Text, nullable=False)
    budget = Column(String(128), nullable=False)
    purchaser = Column(String(256), nullable=False)
    doc_time = Column(String(128), nullable=False)
    project_number = Column(String(128), nullable=True)
    service_period = Column(String(128), nullable=True)
    content = Column(Text, nullable=True)
    source_url = Column(Text, nullable=True)
    source_title = Column(Text, nullable=True)
    extracted_time = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="new", index=True)
    updated_time = Column(String(64), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_name": self.project_name,
            "budget": self.budget,
            "purchaser": self.purchaser,
            "doc_time": self.doc_time,
            "project_number": self.project_number or "",
            "service_period": self.service_period or "",
            "content": self.content or "",
            "source_url": self.source_url or "",
            "source_title": self.source_title or "",
            "extracted_time": self.extracted_time,
            "status": self.status,
            "updated_time": self.updated_time or "",
        }

    @classmethod
    def from_mapping(cls, payload: dict) -> "BidRecord":
        return cls(
            id=payload.get("id"),
            project_name=payload.get("project_name", ""),
            budget=payload.get("budget", ""),
            purchaser=payload.get("purchaser", ""),
            doc_time=payload.get("doc_time", ""),
            project_number=payload.get("project_number"),
            service_period=payload.get("service_period"),
            content=payload.get("content"),
            source_url=payload.get("source_url"),
            source_title=payload.get("source_title"),
            extracted_time=payload.get("extracted_time", ""),
            status=payload.get("status", "new"),
            updated_time=payload.get("updated_time"),
        )
