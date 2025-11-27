"""Authentication manager."""

import functools
from typing import Optional

from flask import session, redirect, url_for, request, g

from models.user import User


class AuthManager:
    """Handle user login/logout and session management."""
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        
    def login(self, username, password) -> bool:
        db_sess = self.db_session_factory()
        try:
            user = db_sess.query(User).filter_by(username=username).first()
            if user and user.check_password(password):
                session.clear()
                session["user_id"] = user.id
                session["username"] = user.username
                return True
            return False
        finally:
            db_sess.close()
            
    def logout(self):
        session.clear()
        
    def change_password(self, user_id, old_password, new_password) -> bool:
        db_sess = self.db_session_factory()
        try:
            user = db_sess.get(User, user_id)
            if not user or not user.check_password(old_password):
                return False
            user.set_password(new_password)
            db_sess.commit()
            return True
        finally:
            db_sess.close()

    def login_required(self, view):
        @functools.wraps(view)
        def wrapped_view(**kwargs):
            if g.user is None:
                return redirect(url_for('login'))
            return view(**kwargs)
        return wrapped_view

    def load_logged_in_user(self):
        user_id = session.get('user_id')
        if user_id is None:
            g.user = None
        else:
            g.user = {"id": user_id, "username": session.get("username")}

