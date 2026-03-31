"""Search orchestrator - fans out queries to all sources and scores results."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Person, PersonEvent, PersonName, SourceMatch, ResearchTask
from ..sources.base import GenealogySource, SourceRecord
from ..sources.familysearch import FamilySearchSource
from ..sources.geneteka import GenetekaSource
from ..sources.findagrave import FindAGraveSource
from ..sources.billiongraves import BillionGravesSource
from ..sources.szukaj import SzukajWArchiwachSource
from ..sources.ellisisland import EllisIslandSource
from ..sources.myheritage import MyHeritageSource
from ..sources.ancestry import AncestrySource
from .confidence import PersonData, compute_confidence

logger = logging.getLogger(__name__)

# All available source instances
SOURCES: dict[str, GenealogySource] = {
    "familysearch": FamilySearchSource(),
    "geneteka": GenetekaSource(),
    "findagrave": FindAGraveSource(),
    "billiongraves": BillionGravesSource(),
    "szukajwarchiwach": SzukajWArchiwachSource(),
    "ellisisland": EllisIslandSource(),
    "myheritage": MyHeritageSource(),
    "ancestry": AncestrySource(),
}


def _person_to_data(person: Person) -> PersonData:
    """Extract searchable data from a Person ORM object."""
    primary_name = next(
        (n for n in person.names if n.is_primary),
        person.names[0] if person.names else None,
    )
    birth_event = next(
        (e for e in person.events if e.event_type == "birth"), None
    )
    death_event = next(
        (e for e in person.events if e.event_type == "death"), None
    )
    return PersonData(
        given_name=primary_name.given_name if primary_name else None,
        surname=primary_name.surname if primary_name else None,
        birth_year=birth_event.date_year if birth_event else None,
        birth_place=birth_event.place_text if birth_event else None,
        death_year=death_event.date_year if death_event else None,
        death_place=death_event.place_text if death_event else None,
    )


def _record_to_candidate(record: SourceRecord) -> PersonData:
    """Convert a SourceRecord to PersonData for scoring."""
    father_given = None
    mother_given = None
    if record.father_name:
        father_given = record.father_name.split()[0] if record.father_name else None
    if record.mother_name:
        mother_given = record.mother_name.split()[0] if record.mother_name else None

    return PersonData(
        given_name=record.given_name,
        surname=record.surname,
        birth_year=record.birth_year,
        birth_place=record.birth_place,
        death_year=record.death_year,
        death_place=record.death_place,
        father_given_name=father_given,
        mother_given_name=mother_given,
    )


async def _search_single_source(
    source: GenealogySource,
    person_data: PersonData,
    task: ResearchTask,
    session: AsyncSession,
    person_id: str,
) -> list[SourceMatch]:
    """Search a single source and persist results."""
    task.status = "running"
    task.started_at = datetime.utcnow()
    await session.flush()

    try:
        records = await source.search_person(
            given_name=person_data.given_name,
            surname=person_data.surname,
            birth_year=person_data.birth_year,
            birth_place=person_data.birth_place,
            death_year=person_data.death_year,
        )

        matches = []
        for record in records:
            candidate = _record_to_candidate(record)
            score, breakdown = compute_confidence(
                person_data, candidate, source.name
            )

            # Only keep matches above a minimum threshold
            if score < 0.2:
                continue

            match = SourceMatch(
                person_id=person_id,
                source_name=source.name,
                source_record_id=record.source_record_id,
                source_url=record.source_url,
                given_name=record.given_name,
                surname=record.surname,
                birth_date=record.birth_date,
                birth_place=record.birth_place,
                death_date=record.death_date,
                death_place=record.death_place,
                father_name=record.father_name,
                mother_name=record.mother_name,
                raw_data=json.dumps(record.raw_data, default=str),
                confidence_score=score,
                confidence_breakdown=json.dumps(breakdown),
                status="pending",
            )
            session.add(match)
            matches.append(match)

        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.result_count = len(matches)
        await session.flush()
        return matches

    except Exception as e:
        logger.exception("Search failed for source %s", source.name)
        task.status = "failed"
        task.completed_at = datetime.utcnow()
        task.error_message = str(e)
        await session.flush()
        return []


async def run_search(
    session: AsyncSession,
    person_id: str,
    source_names: list[str] | None = None,
) -> list[ResearchTask]:
    """Run search across all (or specified) sources for a person.

    Creates ResearchTask records and returns them.
    """
    # Load the person with names and events
    stmt = (
        select(Person)
        .where(Person.id == person_id)
        .options(selectinload(Person.names), selectinload(Person.events))
    )
    result = await session.execute(stmt)
    person = result.scalar_one_or_none()
    if not person:
        raise ValueError(f"Person {person_id} not found")

    person_data = _person_to_data(person)
    if not person_data.surname:
        raise ValueError("Person must have a surname to search")

    # Determine which sources to search
    sources_to_search = source_names or list(SOURCES.keys())
    sources_to_search = [s for s in sources_to_search if s in SOURCES]

    # Create research tasks
    tasks = []
    for source_name in sources_to_search:
        task = ResearchTask(
            person_id=person_id,
            source_name=source_name,
            status="queued",
        )
        session.add(task)
        tasks.append(task)
    await session.flush()

    # Fan out searches concurrently
    await asyncio.gather(
        *[
            _search_single_source(
                SOURCES[task.source_name],
                person_data,
                task,
                session,
                person_id,
            )
            for task in tasks
        ]
    )

    await session.commit()
    return tasks
