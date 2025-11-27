"""User model for authentication."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, String
from werkzeug.security import generate_password_hash, check_password_hash

from core.database import Base


class User(Base):
    """Admin user model."""
    
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True)  # UUID or username
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
    
    @classmethod
    def create_admin(cls, session, username, password):
        user = cls(id="admin", username=username)
        user.set_password(password)
        session.merge(user)  # Update if exists
        session.commit()
        return user
