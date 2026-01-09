"""In-memory session storage for the Karma app."""

from typing import Optional, Any
from models import Session


class SessionStore:
    """Simple in-memory session storage with extended fields for agentic AI."""
    
    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._session_data: dict[str, dict] = {}  # Additional data per session
    
    def create_session(self) -> Session:
        """Create a new session."""
        session = Session()
        self._sessions[session.id] = session
        self._session_data[session.id] = {
            'agent_reasoning': {},
            'current_reasoning': '',
            'tool_calls': [],
            'feedback_history': []
        }
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        session = self._sessions.get(session_id)
        if session:
            # Attach additional data as attributes
            data = self._session_data.get(session_id, {})
            session.agent_reasoning = data.get('agent_reasoning', {})
            session.current_reasoning = data.get('current_reasoning', '')
            session.tool_calls = data.get('tool_calls', [])
            session.feedback_history = data.get('feedback_history', [])
        return session
    
    def update_session(self, session: Session) -> None:
        """Update an existing session."""
        self._sessions[session.id] = session
        
        # Update additional data
        if session.id not in self._session_data:
            self._session_data[session.id] = {}
        
        self._session_data[session.id].update({
            'agent_reasoning': getattr(session, 'agent_reasoning', {}),
            'current_reasoning': getattr(session, 'current_reasoning', ''),
            'tool_calls': getattr(session, 'tool_calls', []),
            'feedback_history': getattr(session, 'feedback_history', [])
        })
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            if session_id in self._session_data:
                del self._session_data[session_id]
            return True
        return False
    
    def get_all_sessions(self) -> list[Session]:
        """Get all sessions (for debugging)."""
        return list(self._sessions.values())
    
    def add_tool_call(self, session_id: str, tool_call: dict) -> None:
        """Add a tool call to session history."""
        if session_id in self._session_data:
            self._session_data[session_id].setdefault('tool_calls', []).append(tool_call)
    
    def add_feedback(self, session_id: str, feedback: dict) -> None:
        """Add feedback to session history."""
        if session_id in self._session_data:
            self._session_data[session_id].setdefault('feedback_history', []).append(feedback)


# Singleton instance
session_store = SessionStore()
