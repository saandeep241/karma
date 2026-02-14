"""Session management routes."""

from fastapi import APIRouter, HTTPException, Depends

from app.models import (
    SetContextRequest, UserContext, TimeAvailable, EnergyLevel
)
from app.auth import require_auth, AuthUser
from app.services.session_store import session_store

router = APIRouter(prefix="/api/session", tags=["sessions"])


@router.post("/create")
async def create_session(user: AuthUser = Depends(require_auth)):
    """Create a new session for the authenticated user."""
    session = session_store.create_session(user.user_id)
    return {"session_id": session.id, "message": "Session created successfully"}


@router.post("/context")
async def set_user_context(request: SetContextRequest, user: AuthUser = Depends(require_auth)):
    """Set the user's current context."""
    session = session_store.get_session(user.user_id, request.session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    context = UserContext(
        time_available=request.time_available,
        energy_level=request.energy_level
    )
    
    session.context = context
    session_store.update_session(session)
    
    return {
        "message": "Context set successfully",
        "context": {
            "time_available": context.time_available.value,
            "energy_level": context.energy_level.value
        }
    }


@router.get("/reasoning/{session_id}")
async def get_agent_reasoning(session_id: str, user: AuthUser = Depends(require_auth)):
    """Get the agent's full reasoning trace for this session."""
    session = session_store.get_session(user.user_id, session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "reasoning": getattr(session, 'agent_reasoning', {}),
        "current_reasoning": getattr(session, 'current_reasoning', '')
    }

