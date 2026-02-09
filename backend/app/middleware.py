"""
Logging and CORS safety-net middleware.
"""

import re
import time
import uuid
from typing import Callable, List, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.logging_config import get_api_logger

logger = get_api_logger()


def _is_origin_allowed_static(
    origin: Optional[str],
    allowed_origins: List[str],
    allow_origin_regex: Optional[str],
) -> bool:
    """Check if Origin is allowed (used by safety net)."""
    if not origin or not origin.strip():
        return False
    origin = origin.strip()
    if origin in allowed_origins:
        return True
    if allow_origin_regex and re.match(allow_origin_regex, origin):
        return True
    base = origin.rstrip("/")
    if base in allowed_origins or (base + "/") == origin:
        return True
    return False


class CORSSafetyNetMiddleware(BaseHTTPMiddleware):
    """
    Ensures CORS headers are on every response when the request had an allowed Origin.
    Handles cases where error responses (401, 403, 404, 500) or OPTIONS might
    otherwise be returned without CORS headers.
    """

    def __init__(
        self,
        app,
        *,
        allowed_origins: List[str],
        allow_origin_regex: Optional[str] = None,
    ):
        super().__init__(app)
        self.allowed_origins = allowed_origins
        self.allow_origin_regex = allow_origin_regex

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        origin = request.headers.get("origin") or request.headers.get("Origin")
        response = await call_next(request)
        if not origin:
            return response
        if not _is_origin_allowed_static(
            origin, self.allowed_origins, self.allow_origin_regex
        ):
            return response
        if response.headers.get("access-control-allow-origin"):
            return response
        # Add CORS headers so the browser does not treat this as a CORS failure
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
        logger.debug(
            f"CORS safety net: added headers for origin {origin!r} "
            f"(status={response.status_code} {request.method} {request.url.path})"
        )
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all incoming requests and outgoing responses.
    Includes timing, status codes, and request details.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())[:8]
        
        # Start timing
        start_time = time.time()
        
        # Extract request info
        method = request.method
        path = request.url.path
        query = str(request.query_params) if request.query_params else ""
        client_ip = request.client.host if request.client else "unknown"
        
        # Log incoming request
        logger.info(
            f"[{request_id}] --> {method} {path}"
            f"{f'?{query}' if query else ''} "
            f"(client: {client_ip})"
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Determine log level based on status code
            status = response.status_code
            if status >= 500:
                log_func = logger.error
                status_icon = "💥"
            elif status >= 400:
                log_func = logger.warning
                status_icon = "⚠️"
            else:
                log_func = logger.info
                status_icon = "✓"
            
            # Log response
            log_func(
                f"[{request_id}] <-- {status_icon} {status} "
                f"({duration_ms:.1f}ms) {method} {path}"
            )
            
            # Add request ID to response headers for debugging
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Log error
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"[{request_id}] <-- 💥 ERROR ({duration_ms:.1f}ms) "
                f"{method} {path}: {type(e).__name__}: {str(e)}"
            )
            raise


class SlowRequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that specifically logs slow requests (over threshold).
    """
    
    SLOW_REQUEST_THRESHOLD_MS = 1000  # 1 second
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        if duration_ms > self.SLOW_REQUEST_THRESHOLD_MS:
            logger.warning(
                f"🐢 SLOW REQUEST: {request.method} {request.url.path} "
                f"took {duration_ms:.1f}ms (threshold: {self.SLOW_REQUEST_THRESHOLD_MS}ms)"
            )
        
        return response

