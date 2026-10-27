"""
Langfuse observability client (v4).

Returns a configured Langfuse instance when LANGFUSE_PUBLIC_KEY and
LANGFUSE_SECRET_KEY are set; otherwise returns None so the app runs
identically without any keys configured.
"""

import uuid as _uuid
import logging
import sys
from contextlib import contextmanager
from functools import lru_cache
from typing import Optional, Dict

logger = logging.getLogger("karma.langfuse")


@contextmanager
def safe_observation(langfuse, **kwargs):
    """Ignore telemetry failures, but never swallow or retry application errors."""
    observation = None
    context = None
    if langfuse is not None:
        try:
            context = langfuse.start_as_current_observation(**kwargs)
            observation = context.__enter__()
        except Exception:
            logger.warning("Langfuse observation start failed; continuing without telemetry",
                           exc_info=True)
            context = None
    try:
        yield observation
    except BaseException:
        # The body may contain a model call or tool with side effects. Do not
        # retry it, let telemetry suppress it, or replace its original error.
        if context is not None:
            try:
                context.__exit__(*sys.exc_info())
            except Exception:
                logger.warning("Langfuse observation exit failed during application error",
                               exc_info=True)
        raise
    else:
        if context is not None:
            try:
                context.__exit__(None, None, None)
            except Exception:
                logger.warning("Langfuse observation exit failed; preserving application result",
                               exc_info=True)


def safe_flush(langfuse):
    """A telemetry flush must not discard a successful application result."""
    if langfuse is not None:
        try:
            langfuse.flush()
        except Exception:
            logger.warning("Langfuse flush failed; preserving application result", exc_info=True)


def safe_update_generation(langfuse, **kwargs):
    if langfuse is not None:
        try:
            langfuse.update_current_generation(**kwargs)
        except Exception:
            logger.warning("Langfuse generation update failed; preserving application result",
                           exc_info=True)

# OpenAI pricing per million tokens (USD), updated May 2025
# Source: https://openai.com/api/pricing
_MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4o":              {"input": 2.50,  "output": 10.00},
    "gpt-4o-2024-11-20":   {"input": 2.50,  "output": 10.00},
    "gpt-4o-2024-08-06":   {"input": 2.50,  "output": 10.00},
    "gpt-4o-2024-05-13":   {"input": 5.00,  "output": 15.00},
    "gpt-4o-mini":         {"input": 0.15,  "output": 0.60},
    "gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo":         {"input": 10.00, "output": 30.00},
    "gpt-4":               {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo":       {"input": 0.50,  "output": 1.50},
}


def compute_cost(model: str, prompt_tokens: int, completion_tokens: int) -> Optional[Dict[str, float]]:
    """
    Return cost_details dict for a Langfuse generation span, or None if the
    model is not in the pricing table.

    Costs are in USD. Langfuse expects cost_details keys to be plain floats.
    """
    pricing = _MODEL_PRICING.get(model)
    if not pricing:
        # Try prefix match for versioned model names not in the table
        for known_model, known_pricing in _MODEL_PRICING.items():
            if model.startswith(known_model):
                pricing = known_pricing
                break

    if not pricing:
        return None

    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return {
        "input": round(input_cost, 8),
        "output": round(output_cost, 8),
        "total": round(input_cost + output_cost, 8),
    }


@contextmanager
def root_trace(name: str, user_id: str = None, operation_type: str = None):
    """
    Open a root Langfuse trace for a single request.

    All agent spans opened via `await` within the same asyncio task will
    automatically nest under this trace through Python contextvars.
    When Langfuse is disabled this is a no-op and yields None.

    Usage (inside an async route handler):
        with root_trace("suggest_task", user_id=user.user_id, operation_type="suggest_task") as tid:
            result = await karma_orchestrator.suggest_task(...)
    """
    langfuse = get_langfuse()
    if not langfuse:
        yield None
        return

    trace_id = _uuid.uuid4().hex
    try:
        with safe_observation(
            langfuse,
            trace_context={"trace_id": trace_id},
            as_type="span",
            name=name,
            metadata={"operation_type": operation_type, "user_id": user_id or "anonymous"},
        ) as observation:
            yield trace_id if observation is not None else None
    finally:
        safe_flush(langfuse)


@lru_cache()
def get_langfuse():
    """Return a Langfuse client, or None if keys are not configured."""
    from app.config import get_settings
    import logging
    settings = get_settings()

    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return None

    try:
        from langfuse import Langfuse
        return Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception as e:
        logging.getLogger("karma.langfuse").warning("Langfuse init failed: %s", e)
        return None
