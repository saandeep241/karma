"""Session store for managing user sessions."""

from typing import Optional
from datetime import datetime

from app.models import Session


class SessionStore:
    """In-memory session storage with user-specific isolation."""
    
    def __init__(self):
        # Nested dict: user_id -> session_id -> Session
        self._sessions: dict[str, dict[str, Session]] = {}
    
    def create_session(self, user_id: str) -> Session:
        """Create a new session for a user."""
        session = Session(user_id=user_id)
        
        # Initialize user's session dict if needed
        if user_id not in self._sessions:
            self._sessions[user_id] = {}
        
        self._sessions[user_id][session.id] = session
        return session
    
    def get_session(self, user_id: str, session_id: str) -> Optional[Session]:
        """Get a session by ID for a specific user."""
        if user_id not in self._sessions:
            return None
        return self._sessions[user_id].get(session_id)
    
    def get_user_sessions(self, user_id: str) -> list[Session]:
        """Get all sessions for a user."""
        if user_id not in self._sessions:
            return []
        return list(self._sessions[user_id].values())
    
    def update_session(self, session: Session) -> None:
        """Update an existing session."""
        user_id = session.user_id
        
        # Ensure user's session dict exists
        if user_id not in self._sessions:
            self._sessions[user_id] = {}
        
        self._sessions[user_id][session.id] = session
    
    def delete_session(self, user_id: str, session_id: str) -> bool:
        """Delete a session for a specific user."""
        if user_id in self._sessions and session_id in self._sessions[user_id]:
            del self._sessions[user_id][session_id]
            return True
        return False
    
    def delete_user_sessions(self, user_id: str) -> int:
        """Delete all sessions for a user."""
        if user_id in self._sessions:
            count = len(self._sessions[user_id])
            del self._sessions[user_id]
            return count
        return 0


# Global session store instance
session_store = SessionStore()

