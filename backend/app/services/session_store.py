"""Session store for managing user sessions."""

from typing import Optional
from datetime import datetime

from app.models import Session


class SessionStore:
    """In-memory session storage."""
    
    def __init__(self):
        self._sessions: dict[str, Session] = {}
    
    def create_session(self) -> Session:
        """Create a new session."""
        session = Session()
        self._sessions[session.id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        return self._sessions.get(session_id)
    
    def update_session(self, session: Session) -> None:
        """Update an existing session."""
        self._sessions[session.id] = session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False


# Global session store instance
session_store = SessionStore()

