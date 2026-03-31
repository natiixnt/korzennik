"""Search and match review endpoints."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Person, PersonEvent, PersonName, Relationship, SourceMatch, ResearchTask
from ..schemas.search import MatchOut, SearchRequest, TaskStatusOut
from ..services.search_orchestrator import run_search

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/{person_id}", response_model=list[TaskStatusOut])
async def trigger_search(
    person_id: str,
    request: SearchRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Trigger async search for a person across sources."""
    sources = request.sources if request else None
    try:
        tasks = await run_search(db, person_id, sources)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return tasks


@router.get("/{person_id}/status", response_model=list[TaskStatusOut])
async def get_search_status(person_id: str, db: AsyncSession = Depends(get_db)):
    """Get status of all search tasks for a person."""
    stmt = (
        select(ResearchTask)
        .where(ResearchTask.person_id == person_id)
        .order_by(ResearchTask.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{person_id}/results", response_model=list[MatchOut])
async def get_search_results(person_id: str, db: AsyncSession = Depends(get_db)):
    """Get all match results for a person, sorted by confidence."""
    stmt = (
        select(SourceMatch)
        .where(SourceMatch.person_id == person_id)
        .order_by(SourceMatch.confidence_score.desc())
    )
    result = await db.execute(stmt)
    matches = result.scalars().all()

    # Parse confidence_breakdown JSON for response
    out = []
    for m in matches:
        match_dict = {
            "id": m.id,
            "person_id": m.person_id,
            "source_name": m.source_name,
            "source_record_id": m.source_record_id,
            "source_url": m.source_url,
            "given_name": m.given_name,
            "surname": m.surname,
            "birth_date": m.birth_date,
            "birth_place": m.birth_place,
            "death_date": m.death_date,
            "death_place": m.death_place,
            "father_name": m.father_name,
            "mother_name": m.mother_name,
            "confidence_score": m.confidence_score,
            "confidence_breakdown": json.loads(m.confidence_breakdown)
            if m.confidence_breakdown
            else None,
            "status": m.status,
        }
        out.append(MatchOut(**match_dict))
    return out


@router.post("/matches/{match_id}/confirm", response_model=MatchOut)
async def confirm_match(match_id: int, db: AsyncSession = Depends(get_db)):
    """Confirm a match and optionally create new persons from discovered relatives."""
    stmt = select(SourceMatch).where(SourceMatch.id == match_id)
    result = await db.execute(stmt)
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match.status = "confirmed"
    match.reviewed_at = datetime.utcnow()

    # If the match contains parent info not yet in the tree, create them
    if match.father_name:
        parts = match.father_name.split(maxsplit=1)
        father_given = parts[0] if parts else None
        father_surname = parts[1] if len(parts) > 1 else match.surname
        # Check if a parent relationship already exists
        existing = await db.execute(
            select(Relationship).where(
                Relationship.person2_id == match.person_id,
                Relationship.rel_type == "parent_child",
            )
        )
        existing_parents = existing.scalars().all()
        father_exists = False
        for rel in existing_parents:
            parent = await db.get(Person, rel.person1_id)
            if parent and parent.gender == "M":
                father_exists = True
                break

        if not father_exists and father_given:
            father = Person(gender="M", origin="confirmed_match")
            db.add(father)
            await db.flush()
            db.add(PersonName(
                person_id=father.id,
                given_name=father_given,
                surname=father_surname,
                name_type="birth",
                is_primary=True,
            ))
            db.add(Relationship(
                person1_id=father.id,
                person2_id=match.person_id,
                rel_type="parent_child",
                confidence=match.confidence_score,
                source=match.source_name,
            ))

    if match.mother_name:
        parts = match.mother_name.split(maxsplit=1)
        mother_given = parts[0] if parts else None
        mother_surname = parts[1] if len(parts) > 1 else None
        existing = await db.execute(
            select(Relationship).where(
                Relationship.person2_id == match.person_id,
                Relationship.rel_type == "parent_child",
            )
        )
        existing_parents = existing.scalars().all()
        mother_exists = False
        for rel in existing_parents:
            parent = await db.get(Person, rel.person1_id)
            if parent and parent.gender == "F":
                mother_exists = True
                break

        if not mother_exists and mother_given:
            mother = Person(gender="F", origin="confirmed_match")
            db.add(mother)
            await db.flush()
            db.add(PersonName(
                person_id=mother.id,
                given_name=mother_given,
                surname=mother_surname,
                name_type="birth",
                is_primary=True,
            ))
            db.add(Relationship(
                person1_id=mother.id,
                person2_id=match.person_id,
                rel_type="parent_child",
                confidence=match.confidence_score,
                source=match.source_name,
            ))

    await db.commit()

    return MatchOut(
        id=match.id,
        person_id=match.person_id,
        source_name=match.source_name,
        source_record_id=match.source_record_id,
        source_url=match.source_url,
        given_name=match.given_name,
        surname=match.surname,
        birth_date=match.birth_date,
        birth_place=match.birth_place,
        death_date=match.death_date,
        death_place=match.death_place,
        father_name=match.father_name,
        mother_name=match.mother_name,
        confidence_score=match.confidence_score,
        confidence_breakdown=json.loads(match.confidence_breakdown)
        if match.confidence_breakdown
        else None,
        status=match.status,
    )


@router.post("/matches/{match_id}/reject", response_model=MatchOut)
async def reject_match(match_id: int, db: AsyncSession = Depends(get_db)):
    """Reject a match."""
    stmt = select(SourceMatch).where(SourceMatch.id == match_id)
    result = await db.execute(stmt)
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match.status = "rejected"
    match.reviewed_at = datetime.utcnow()
    await db.commit()

    return MatchOut(
        id=match.id,
        person_id=match.person_id,
        source_name=match.source_name,
        source_record_id=match.source_record_id,
        source_url=match.source_url,
        given_name=match.given_name,
        surname=match.surname,
        birth_date=match.birth_date,
        birth_place=match.birth_place,
        death_date=match.death_date,
        death_place=match.death_place,
        father_name=match.father_name,
        mother_name=match.mother_name,
        confidence_score=match.confidence_score,
        confidence_breakdown=json.loads(match.confidence_breakdown)
        if match.confidence_breakdown
        else None,
        status=match.status,
    )
