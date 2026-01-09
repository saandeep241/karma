"""Session management routes."""

from fastapi import APIRouter, HTTPException

from app.models import (
    SetContextRequest, UserContext, TimeAvailable, EnergyLevel, EmotionalState
)
from app.services.session_store import session_store

router = APIRouter(prefix="/api/session", tags=["sessions"])


@router.post("/create")
async def create_session():
    """Create a new session."""
    session = session_store.create_session()
    return {"session_id": session.id, "message": "Session created successfully"}


@router.post("/context")
async def set_user_context(request: SetContextRequest):
    """Set the user's current context."""
    session = session_store.get_session(request.session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    context = UserContext(
        time_available=request.time_available,
        energy_level=request.energy_level,
        emotional_state=request.emotional_state
    )
    
    session.context = context
    session_store.update_session(session)
    
    return {
        "message": "Context set successfully",
        "context": {
            "time_available": context.time_available.value,
            "energy_level": context.energy_level.value,
            "emotional_state": context.emotional_state.value if context.emotional_state else None
        }
    }


@router.get("/reasoning/{session_id}")
async def get_agent_reasoning(session_id: str):
    """Get the agent's full reasoning trace for this session."""
    session = session_store.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "reasoning": getattr(session, 'agent_reasoning', {}),
        "current_reasoning": getattr(session, 'current_reasoning', '')
    }

