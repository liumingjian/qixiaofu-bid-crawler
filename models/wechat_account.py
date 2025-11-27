"""WeChat account database model."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import Session

from core.database import Base


class WeChatAccount(Base):
    """WeChat public account model."""
    
    __tablename__ = "wechat_accounts"
    
    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    fakeid = Column(String(200), nullable=False)
    token = Column(String(200), nullable=False)
    cookie = Column(Text, nullable=False)
    page_size = Column(Integer, default=5)
    article_limit = Column(Integer, default=10)  # Number of recent articles to fetch
    # Filter settings (JSON encoded list for keywords)
    filter_keywords = Column(Text, nullable=True)
    filter_keyword_logic = Column(String(10), default="OR")  # OR / AND
    
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        """Convert model to dictionary."""
        import json
        keywords = []
        if self.filter_keywords:
            try:
                keywords = json.loads(self.filter_keywords)
            except:
                keywords = []

        return {
            "id": self.id,
            "name": self.name,
            "fakeid": self.fakeid,
            "token": self.token,
            "cookie": self.cookie,
            "page_size": self.page_size,
            "article_limit": self.article_limit,
            "filter_keywords": keywords,
            "filter_keyword_logic": self.filter_keyword_logic or "OR",
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'WeChatAccount':
        """Create model from dictionary."""
        import json
        keywords = data.get("filter_keywords", [])
        if isinstance(keywords, list):
            keywords_json = json.dumps(keywords, ensure_ascii=False)
        else:
            keywords_json = "[]"

        return cls(
            id=data.get("id"),
            name=data["name"],
            fakeid=data.get("fakeid", ""),
            token=data.get("token", ""),
            cookie=data.get("cookie", ""),
            page_size=data.get("page_size", 5),
            article_limit=data.get("article_limit", 10),
            filter_keywords=keywords_json,
            filter_keyword_logic=data.get("filter_keyword_logic", "OR"),
            enabled=data.get("enabled", True)
        )
    
    @classmethod
    def get_all(cls, session: Session, enabled_only: bool = False) -> List['WeChatAccount']:
        """Get all accounts."""
        query = session.query(cls)
        if enabled_only:
            query = query.filter(cls.enabled == True)
        return query.all()
    
    @classmethod
    def get_by_id(cls, session: Session, account_id: str) -> Optional['WeChatAccount']:
        """Get account by ID."""
        return session.query(cls).filter(cls.id == account_id).first()
    
    @classmethod
    def create(cls, session: Session, data: Dict) -> 'WeChatAccount':
        """Create new account."""
        account = cls.from_dict(data)
        session.add(account)
        session.commit()
        session.refresh(account)
        return account
    
    @classmethod
    def update(cls, session: Session, account_id: str, data: Dict) -> Optional['WeChatAccount']:
        """Update existing account."""
        import json
        account = cls.get_by_id(session, account_id)
        if not account:
            return None
        
        for key, value in data.items():
            if key == 'filter_keywords' and isinstance(value, list):
                setattr(account, key, json.dumps(value, ensure_ascii=False))
            elif hasattr(account, key) and key not in ['id', 'created_at']:
                setattr(account, key, value)
        
        account.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(account)
        return account
    
    @classmethod
    def delete(cls, session: Session, account_id: str) -> bool:
        """Delete account by ID."""
        account = cls.get_by_id(session, account_id)
        if not account:
            return False
        
        session.delete(account)
        session.commit()
        return True
