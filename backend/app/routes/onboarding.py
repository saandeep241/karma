import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.models import Task
from app.auth import require_auth, AuthUser
from app.services import db_service
from app.agents import karma_orchestrator
from app.logging_config import get_api_logger

logger = get_api_logger()

router = APIRouter(prefix="/api", tags=["onboarding"])

STARTER_TASKS_PATH = Path(__file__).resolve().parent.parent / "config" / "starter_tasks.json"

_starter_tasks_cache: dict | None = None


def _load_starter_tasks() -> dict:
    global _starter_tasks_cache
    if _starter_tasks_cache is not None:
        return _starter_tasks_cache
    try:
        with open(STARTER_TASKS_PATH, "r") as f:
            _starter_tasks_cache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.error(f"Failed to load starter tasks config: {exc}")
        _starter_tasks_cache = {}
    return _starter_tasks_cache


class OnboardingRequest(BaseModel):
    task_text: Optional[str] = None
    categories: list[str] = []


class OnboardingResponse(BaseModel):
    tasks_created: int
    tasks: list[dict]


@router.post("/onboarding/complete", response_model=OnboardingResponse)
async def complete_onboarding(
    request: OnboardingRequest,
    user: AuthUser = Depends(require_auth),
):
    logger.info(f"Onboarding started for user_id={user.user_id}")

    raw_tasks: list[Task] = []

    if request.task_text and request.task_text.strip():
        items = [t.strip() for t in request.task_text.split(",")]
        for item in items:
            if item:
                raw_tasks.append(Task(text=item))

    if request.categories:
        starter_catalog = _load_starter_tasks()
        valid_categories = set(starter_catalog.keys())
        invalid = [c for c in request.categories if c not in valid_categories]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown categories: {', '.join(invalid)}. Valid categories: {', '.join(sorted(valid_categories))}",
            )
        for category in request.categories:
            for entry in starter_catalog[category]:
                task = Task(
                    text=entry["text"],
                    estimated_minutes=entry.get("estimated_minutes"),
                    energy_required=entry.get("energy_required"),
                )
                raw_tasks.append(task)

    if not raw_tasks:
        raise HTTPException(
            status_code=400,
            detail="No tasks provided. Please enter tasks or select at least one category.",
        )

    logger.info(f"Onboarding: processing {len(raw_tasks)} tasks through TaskAnalyzer")

    analyzed_tasks, _ = await karma_orchestrator.analyze_tasks(
        raw_tasks,
        user_id=user.user_id,
        include_enrichment=False,
    )

    today = datetime.now().strftime("%Y-%m-%d")
    saved: list[dict] = []

    for task in analyzed_tasks:
        task_dict = task.model_dump(by_alias=False)
        task_dict["date"] = today
        await db_service.save_task(user.user_id, task_dict)
        saved.append(task_dict)
        logger.debug(f"Saved onboarding task: {task.id} - {task.text[:50]}")

    await db_service.mark_onboarding_complete(user.user_id)
    logger.info(f"Onboarding complete: {len(saved)} tasks created for user_id={user.user_id}")

    return OnboardingResponse(tasks_created=len(saved), tasks=saved)
