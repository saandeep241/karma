"""
Presentation routes for slide viewer with code execution.
"""
import json
import sys
import io
import traceback
import base64
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/presentation", tags=["presentation"])


class CodeExecutionRequest(BaseModel):
    code: str
    session_id: Optional[str] = "default"


class CodeExecutionResponse(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None
    figures: list[str] = []  # Base64 encoded images


class SlideResponse(BaseModel):
    id: int
    title: str
    type: str
    content: str
    code: Optional[str]
    notes: Optional[str]


class PresentationResponse(BaseModel):
    title: str
    subtitle: str
    slides: list[SlideResponse]


# Store execution contexts per session
_execution_contexts: dict[str, dict] = {}


def get_execution_context(session_id: str) -> dict:
    """Get or create an execution context for a session."""
    if session_id not in _execution_contexts:
        # Initialize with common imports
        context = {
            "__builtins__": __builtins__,
            "__name__": "__main__",
        }
        _execution_contexts[session_id] = context
    return _execution_contexts[session_id]


@router.get("/slides", response_model=PresentationResponse)
async def get_slides():
    """Load the presentation slides from the JSON file."""
    # Look for slides.json in the expected location
    slides_paths = [
        Path("/Users/sandy/noble-common/noble_common/core/data_interface/notebooks/ensemble_GL/slides.json"),
        Path("./slides.json"),
        Path("../slides.json"),
    ]
    
    slides_file = None
    for path in slides_paths:
        if path.exists():
            slides_file = path
            break
    
    if slides_file is None:
        raise HTTPException(status_code=404, detail="Slides file not found")
    
    try:
        with open(slides_file) as f:
            data = json.load(f)
        return PresentationResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading slides: {str(e)}")


@router.post("/execute", response_model=CodeExecutionResponse)
async def execute_code(request: CodeExecutionRequest):
    """Execute Python code and return output."""
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    
    context = get_execution_context(request.session_id)
    
    # Capture stdout
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = captured_stdout = io.StringIO()
    sys.stderr = captured_stderr = io.StringIO()
    
    figures: list[str] = []
    error_msg: Optional[str] = None
    success = True
    
    try:
        # Close any existing figures
        plt.close('all')
        
        # Execute the code
        exec(request.code, context)
        
        # Capture any matplotlib figures
        for fig_num in plt.get_fignums():
            fig = plt.figure(fig_num)
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            figures.append(f"data:image/png;base64,{img_base64}")
            plt.close(fig)
            
    except Exception as e:
        success = False
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    output = captured_stdout.getvalue()
    stderr_output = captured_stderr.getvalue()
    
    if stderr_output and not error_msg:
        output += f"\n[stderr]: {stderr_output}"
    
    return CodeExecutionResponse(
        success=success,
        output=output,
        error=error_msg,
        figures=figures
    )


@router.post("/reset")
async def reset_session(session_id: str = "default"):
    """Reset the execution context for a session."""
    if session_id in _execution_contexts:
        del _execution_contexts[session_id]
    return {"message": f"Session {session_id} reset"}


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "presentation"}

