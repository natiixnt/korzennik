"""Auto-discovery API endpoints for recursive ancestor search."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db, async_session
from ..models import Person
from ..services.auto_discovery import (
    DiscoveryProgress,
    get_discovery_progress,
    run_auto_discovery,
    _active_runs,
)

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


class DiscoveryRequest(BaseModel):
    person_ids: list[str] | None = None  # None = all persons
    max_depth: int = 10
    auto_confirm_threshold: float = 0.75


class DiscoveryStartResponse(BaseModel):
    run_id: str
    status: str
    message: str


class DiscoveryProgressResponse(BaseModel):
    run_id: str
    status: str
    total_persons: int
    searched_persons: int
    matches_found: int
    auto_confirmed: int
    cross_validated: int
    new_persons_created: int
    persons_enriched: int
    current_person: str | None
    current_depth: int
    errors: list[str]
    log: list[str]


# Background tasks tracking
_background_tasks: dict[str, asyncio.Task] = {}


async def _run_discovery_background(
    run_id: str,
    person_ids: list[str] | None,
    max_depth: int,
    auto_confirm_threshold: float,
):
    """Run discovery in background with its own DB session."""
    async with async_session() as session:
        await run_auto_discovery(
            session=session,
            run_id=run_id,
            start_person_ids=person_ids,
            max_depth=max_depth,
            auto_confirm_threshold=auto_confirm_threshold,
        )


@router.post("/start", response_model=DiscoveryStartResponse)
async def start_discovery(
    request: DiscoveryRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Start automatic recursive ancestor discovery.

    This runs in the background. Use GET /api/discovery/{run_id}/progress
    to track progress.
    """
    run_id = str(uuid.uuid4())[:8]
    req = request or DiscoveryRequest()

    # Validate person IDs if provided
    if req.person_ids:
        for pid in req.person_ids:
            stmt = select(Person.id).where(Person.id == pid)
            result = await db.execute(stmt)
            if not result.scalar_one_or_none():
                raise HTTPException(404, f"Person {pid} not found")

    # Launch background task
    task = asyncio.create_task(
        _run_discovery_background(
            run_id=run_id,
            person_ids=req.person_ids,
            max_depth=req.max_depth,
            auto_confirm_threshold=req.auto_confirm_threshold,
        )
    )
    _background_tasks[run_id] = task

    return DiscoveryStartResponse(
        run_id=run_id,
        status="started",
        message=f"Odkrywanie uruchomione (max {req.max_depth} pokolen)",
    )


@router.get("/{run_id}/progress", response_model=DiscoveryProgressResponse)
async def get_progress(run_id: str):
    """Get progress of an auto-discovery run."""
    progress = get_discovery_progress(run_id)
    if not progress:
        raise HTTPException(404, "Discovery run not found")

    return DiscoveryProgressResponse(
        run_id=run_id,
        status=progress.status,
        total_persons=progress.total_persons,
        searched_persons=progress.searched_persons,
        matches_found=progress.matches_found,
        auto_confirmed=progress.auto_confirmed,
        cross_validated=progress.cross_validated,
        new_persons_created=progress.new_persons_created,
        persons_enriched=progress.persons_enriched,
        current_person=progress.current_person,
        current_depth=progress.current_depth,
        errors=progress.errors,
        log=progress.log[-50:],  # Last 50 log entries
    )


@router.post("/{run_id}/stop")
async def stop_discovery(run_id: str):
    """Stop a running discovery."""
    task = _background_tasks.get(run_id)
    if task and not task.done():
        task.cancel()
        progress = get_discovery_progress(run_id)
        if progress:
            progress.status = "stopped"
        return {"status": "stopped"}
    raise HTTPException(404, "Discovery run not found or already finished")


@router.get("/runs", response_model=list[DiscoveryProgressResponse])
async def list_runs():
    """List all discovery runs."""
    runs = []
    for run_id, progress in _active_runs.items():
        runs.append(DiscoveryProgressResponse(
            run_id=run_id,
            status=progress.status,
            total_persons=progress.total_persons,
            searched_persons=progress.searched_persons,
            matches_found=progress.matches_found,
            auto_confirmed=progress.auto_confirmed,
            cross_validated=progress.cross_validated,
            new_persons_created=progress.new_persons_created,
            persons_enriched=progress.persons_enriched,
            current_person=progress.current_person,
            current_depth=progress.current_depth,
            errors=progress.errors,
            log=progress.log[-10:],
        ))
    return runs
