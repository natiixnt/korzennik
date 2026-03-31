"""Automatic recursive ancestor discovery engine.

When triggered, this engine:
1. Searches all sources for each person in the tree
2. Auto-confirms high-confidence matches (>= threshold)
3. Cross-validates matches across multiple sources
4. Extracts newly discovered relatives (parents, spouses)
5. Creates Person nodes for discovered relatives
6. Recursively searches for the newly discovered relatives
7. Enriches existing persons with new data from confirmed matches
8. Tracks progress for the UI to display
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Person, PersonEvent, PersonName, Relationship, SourceMatch, ResearchTask
from ..sources.base import SourceRecord
from .confidence import PersonData, compute_confidence
from .search_orchestrator import (
    SOURCES,
    _person_to_data,
    _record_to_candidate,
    _search_single_source,
)

logger = logging.getLogger(__name__)

# Thresholds for automatic decisions
AUTO_CONFIRM_THRESHOLD = 0.75  # Auto-confirm matches above this score
CROSS_VALIDATED_THRESHOLD = 0.60  # Lower threshold if validated by 2+ sources
MIN_SEARCH_THRESHOLD = 0.3  # Minimum data quality to bother searching

# Maximum recursion depth (generations)
MAX_DEPTH = 10

# Maximum persons to process in one discovery run
MAX_PERSONS_PER_RUN = 200


@dataclass
class DiscoveryProgress:
    """Tracks progress of an auto-discovery run."""
    total_persons: int = 0
    searched_persons: int = 0
    matches_found: int = 0
    auto_confirmed: int = 0
    cross_validated: int = 0
    new_persons_created: int = 0
    persons_enriched: int = 0
    current_person: str | None = None
    current_depth: int = 0
    status: str = "running"  # running | completed | failed
    errors: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)


# Global progress tracker (keyed by session/run)
_active_runs: dict[str, DiscoveryProgress] = {}


def get_discovery_progress(run_id: str) -> DiscoveryProgress | None:
    return _active_runs.get(run_id)


async def run_auto_discovery(
    session: AsyncSession,
    run_id: str,
    start_person_ids: list[str] | None = None,
    max_depth: int = MAX_DEPTH,
    auto_confirm_threshold: float = AUTO_CONFIRM_THRESHOLD,
) -> DiscoveryProgress:
    """Run automatic recursive ancestor discovery.

    If start_person_ids is None, processes all persons in the tree.
    Discovers ancestors by searching all sources, auto-confirming
    high-confidence matches, and recursively searching newly found relatives.
    """
    progress = DiscoveryProgress()
    _active_runs[run_id] = progress

    try:
        # Determine starting persons
        if start_person_ids:
            person_ids = set(start_person_ids)
        else:
            stmt = select(Person.id)
            result = await session.execute(stmt)
            person_ids = {row[0] for row in result.all()}

        progress.total_persons = len(person_ids)
        progress.log.append(f"Rozpoczynam odkrywanie dla {len(person_ids)} osob")

        # Track which persons have been searched to avoid cycles
        searched: set[str] = set()
        # Queue: (person_id, depth)
        queue: list[tuple[str, int]] = [(pid, 0) for pid in person_ids]

        while queue and len(searched) < MAX_PERSONS_PER_RUN:
            person_id, depth = queue.pop(0)

            if person_id in searched:
                continue
            if depth > max_depth:
                continue

            searched.add(person_id)
            progress.searched_persons = len(searched)
            progress.current_person = person_id
            progress.current_depth = depth

            # Load the person
            stmt = (
                select(Person)
                .where(Person.id == person_id)
                .options(selectinload(Person.names), selectinload(Person.events))
            )
            result = await session.execute(stmt)
            person = result.scalar_one_or_none()
            if not person:
                continue

            person_data = _person_to_data(person)
            if not person_data.surname:
                continue

            # Check if this person has enough data to search meaningfully
            if not _has_enough_data(person_data):
                progress.log.append(
                    f"  Pominieto {_format_name(person)} - za malo danych do wyszukiwania"
                )
                continue

            name_str = _format_name(person)
            progress.log.append(f"Szukam: {name_str} (pokolenie {depth})")

            # Search all sources
            all_matches = await _search_all_sources(session, person_id, person_data)
            progress.matches_found += len(all_matches)

            if not all_matches:
                progress.log.append(f"  Brak wynikow dla {name_str}")
                continue

            progress.log.append(f"  Znaleziono {len(all_matches)} wynikow dla {name_str}")

            # Cross-validate: group matches by the person they describe
            validated_matches = _cross_validate_matches(all_matches, auto_confirm_threshold)

            # Auto-confirm validated matches and extract new relatives
            for match_group in validated_matches:
                best_match = match_group[0]  # Highest confidence in the group

                # Auto-confirm
                best_match.status = "confirmed"
                best_match.reviewed_at = datetime.utcnow()
                progress.auto_confirmed += 1

                if len(match_group) > 1:
                    progress.cross_validated += 1
                    progress.log.append(
                        f"  Potwierdzono krzyzowo ({len(match_group)} zrodel): "
                        f"{best_match.given_name} {best_match.surname} "
                        f"(pewnosc: {best_match.confidence_score:.0%})"
                    )

                # Enrich the existing person with data from the match
                enriched = await _enrich_person(session, person, best_match)
                if enriched:
                    progress.persons_enriched += 1

                # Extract and create newly discovered relatives
                new_person_ids = await _extract_relatives(
                    session, person, best_match, match_group
                )
                progress.new_persons_created += len(new_person_ids)

                # Add newly discovered persons to the queue for recursive search
                for new_id in new_person_ids:
                    if new_id not in searched:
                        queue.append((new_id, depth + 1))
                        progress.total_persons += 1

            await session.commit()

        progress.status = "completed"
        progress.log.append(
            f"Zakonczono: przeszukano {progress.searched_persons} osob, "
            f"potwierdzono {progress.auto_confirmed} wynikow, "
            f"odkryto {progress.new_persons_created} nowych osob"
        )

    except Exception as e:
        logger.exception("Auto-discovery failed")
        progress.status = "failed"
        progress.errors.append(str(e))

    return progress


def _has_enough_data(person_data: PersonData) -> bool:
    """Check if a person has enough data to search meaningfully."""
    if not person_data.surname:
        return False
    # Need at least a name - given name + surname, or surname + year/place
    has_given = bool(person_data.given_name)
    has_year = person_data.birth_year is not None or person_data.death_year is not None
    has_place = bool(person_data.birth_place)
    return has_given or has_year or has_place


def _format_name(person: Person) -> str:
    """Format a person's name for logging."""
    name = next((n for n in person.names if n.is_primary), person.names[0] if person.names else None)
    if name:
        return f"{name.given_name or '?'} {name.surname or '?'}"
    return "???"


async def _search_all_sources(
    session: AsyncSession,
    person_id: str,
    person_data: PersonData,
) -> list[SourceMatch]:
    """Search all sources for a person.

    First fires all HTTP requests concurrently to fetch records,
    then scores and persists results sequentially (avoids SQLite locking).
    """
    # Step 1: Fire all HTTP searches concurrently (no DB writes)
    async def _fetch(source: GenealogySource) -> list[SourceRecord]:
        try:
            return await source.search_person(
                given_name=person_data.given_name,
                surname=person_data.surname,
                birth_year=person_data.birth_year,
                birth_place=person_data.birth_place,
                death_year=person_data.death_year,
            )
        except Exception as e:
            logger.error("Search failed for %s: %s", source.name, e)
            return []

    fetch_results = await asyncio.gather(
        *[_fetch(source) for source in SOURCES.values()],
        return_exceptions=True,
    )

    # Step 2: Score and persist results sequentially
    all_matches: list[SourceMatch] = []
    for (source_name, source), result in zip(SOURCES.items(), fetch_results):
        if isinstance(result, Exception):
            logger.error("Source %s failed: %s", source_name, result)
            continue

        records: list[SourceRecord] = result

        # Create research task
        task = ResearchTask(
            person_id=person_id,
            source_name=source_name,
            status="completed",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            result_count=0,
        )
        session.add(task)

        for record in records:
            candidate = _record_to_candidate(record)
            score, breakdown = compute_confidence(
                person_data, candidate, source_name
            )
            if score < 0.2:
                continue

            match = SourceMatch(
                person_id=person_id,
                source_name=source_name,
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
            all_matches.append(match)
            task.result_count += 1

        await session.flush()

    return all_matches


def _cross_validate_matches(
    matches: list[SourceMatch],
    auto_confirm_threshold: float,
) -> list[list[SourceMatch]]:
    """Group and cross-validate matches.

    Returns groups of matches that describe the same person and meet
    the confidence threshold for auto-confirmation.

    Strategy:
    - Group matches by similarity (same name + similar dates)
    - A match is auto-confirmed if:
      a) Single source with score >= auto_confirm_threshold, OR
      b) Multiple sources agree (cross-validated) with score >= lower threshold
    """
    if not matches:
        return []

    # Sort by confidence descending
    sorted_matches = sorted(matches, key=lambda m: m.confidence_score, reverse=True)

    # Group matches that describe the same person
    groups: list[list[SourceMatch]] = []
    used = set()

    for i, match_a in enumerate(sorted_matches):
        if i in used:
            continue

        group = [match_a]
        used.add(i)

        for j, match_b in enumerate(sorted_matches[i + 1:], start=i + 1):
            if j in used:
                continue
            if _matches_same_person(match_a, match_b):
                group.append(match_b)
                used.add(j)

        groups.append(group)

    # Filter groups that meet auto-confirm criteria
    confirmed_groups = []
    for group in groups:
        best_score = group[0].confidence_score
        num_sources = len({m.source_name for m in group})

        if best_score >= auto_confirm_threshold:
            confirmed_groups.append(group)
        elif num_sources >= 2 and best_score >= CROSS_VALIDATED_THRESHOLD:
            # Cross-validated by multiple sources
            confirmed_groups.append(group)

    return confirmed_groups


def _matches_same_person(a: SourceMatch, b: SourceMatch) -> bool:
    """Check if two matches likely describe the same person.

    Uses the Polish matching engine for name comparison (handles
    Kowalski/Kowalska, Joannes/Jan, etc.) and historical place
    name matching (Breslau/Wroclaw, etc.).
    """
    from ..matching.engine import match_given_names, match_surnames
    from ..matching.places import places_match

    # Same source record = definitely same
    if a.source_record_id == b.source_record_id:
        return True

    # Use the matching engine for name comparison
    surname_score = match_surnames(a.surname or "", b.surname or "")
    given_score = match_given_names(a.given_name or "", b.given_name or "")
    name_score = (surname_score + given_score) / 2

    if name_score < 0.5:
        return False

    # Names match well enough - check supporting evidence
    # Birth dates close?
    year_a = _extract_year(a.birth_date)
    year_b = _extract_year(b.birth_date)
    if year_a and year_b and abs(year_a - year_b) <= 3:
        return True

    # Birth places match (with historical equivalences)?
    if a.birth_place and b.birth_place:
        place_score = places_match(a.birth_place, b.birth_place)
        if place_score >= 0.7:
            return True

    # Strong name match alone (e.g., exact match) is enough
    if name_score >= 0.85:
        return True

    return False


def _extract_year(date_text: str | None) -> int | None:
    if not date_text:
        return None
    match = re.search(r"(\d{4})", date_text)
    return int(match.group(1)) if match else None


async def _enrich_person(
    session: AsyncSession,
    person: Person,
    match: SourceMatch,
) -> bool:
    """Enrich existing person data with information from a confirmed match.

    Adds missing events (birth/death dates/places) that the match provides
    but the person doesn't have yet.
    """
    enriched = False

    # Check for missing birth info
    birth_event = next((e for e in person.events if e.event_type == "birth"), None)
    if not birth_event and (match.birth_date or match.birth_place):
        year = _extract_year(match.birth_date)
        session.add(PersonEvent(
            person_id=person.id,
            event_type="birth",
            date_text=match.birth_date,
            date_year=year,
            place_text=match.birth_place,
        ))
        enriched = True
    elif birth_event:
        # Fill in missing fields
        if not birth_event.date_text and match.birth_date:
            birth_event.date_text = match.birth_date
            birth_event.date_year = _extract_year(match.birth_date)
            enriched = True
        if not birth_event.place_text and match.birth_place:
            birth_event.place_text = match.birth_place
            enriched = True

    # Check for missing death info
    death_event = next((e for e in person.events if e.event_type == "death"), None)
    if not death_event and (match.death_date or match.death_place):
        year = _extract_year(match.death_date)
        session.add(PersonEvent(
            person_id=person.id,
            event_type="death",
            date_text=match.death_date,
            date_year=year,
            place_text=match.death_place,
        ))
        enriched = True
    elif death_event:
        if not death_event.date_text and match.death_date:
            death_event.date_text = match.death_date
            death_event.date_year = _extract_year(match.death_date)
            enriched = True
        if not death_event.place_text and match.death_place:
            death_event.place_text = match.death_place
            enriched = True

    return enriched


async def _extract_relatives(
    session: AsyncSession,
    person: Person,
    best_match: SourceMatch,
    match_group: list[SourceMatch],
) -> list[str]:
    """Extract newly discovered relatives from a confirmed match group.

    Creates Person nodes for parents (and spouses if found) that don't
    already exist in the tree. Returns list of new person IDs.
    """
    new_ids = []

    # Collect parent names from all matches in the group (more data = better)
    father_names: list[str] = []
    mother_names: list[str] = []
    for match in match_group:
        if match.father_name:
            father_names.append(match.father_name)
        if match.mother_name:
            mother_names.append(match.mother_name)

    # Use the most common father/mother name across sources
    father_name = _most_common(father_names) if father_names else None
    mother_name = _most_common(mother_names) if mother_names else None

    # Check existing parent relationships
    existing_rels = await session.execute(
        select(Relationship).where(
            Relationship.person2_id == person.id,
            Relationship.rel_type == "parent_child",
        )
    )
    existing_parent_rels = existing_rels.scalars().all()
    existing_parent_ids = [r.person1_id for r in existing_parent_rels]

    # Load existing parents to check gender
    has_father = False
    has_mother = False
    for pid in existing_parent_ids:
        parent = await session.get(Person, pid)
        if parent:
            if parent.gender == "M":
                has_father = True
            elif parent.gender == "F":
                has_mother = True

    # Create father if not exists
    if father_name and not has_father:
        father_id = await _create_relative(
            session, father_name, "M", person, best_match
        )
        if father_id:
            new_ids.append(father_id)

    # Create mother if not exists
    if mother_name and not has_mother:
        mother_id = await _create_relative(
            session, mother_name, "F", person, best_match
        )
        if mother_id:
            new_ids.append(mother_id)

    return new_ids


async def _create_relative(
    session: AsyncSession,
    full_name: str,
    gender: str,
    child: Person,
    match: SourceMatch,
) -> str | None:
    """Create a new Person for a discovered relative and link to the child."""
    parts = full_name.strip().split(maxsplit=1)
    given_name = parts[0] if parts else None
    surname = parts[1] if len(parts) > 1 else None

    if not given_name:
        return None

    # If no surname found, infer from the child
    if not surname:
        child_name = next((n for n in child.names if n.is_primary), None)
        if child_name:
            surname = child_name.surname

    # Estimate birth year (parent ~25 years older)
    child_birth = next((e for e in child.events if e.event_type == "birth"), None)
    parent_birth_year = None
    if child_birth and child_birth.date_year:
        parent_birth_year = child_birth.date_year - 25

    # Create the person
    parent = Person(gender=gender, origin="auto_discovered")
    session.add(parent)
    await session.flush()

    session.add(PersonName(
        person_id=parent.id,
        given_name=given_name,
        surname=surname,
        name_type="birth",
        is_primary=True,
    ))

    # Add estimated birth event if we have data
    if parent_birth_year:
        session.add(PersonEvent(
            person_id=parent.id,
            event_type="birth",
            date_text=f"~{parent_birth_year}",
            date_year=parent_birth_year,
            place_text=child_birth.place_text if child_birth else None,
        ))

    # Create parent-child relationship
    session.add(Relationship(
        person1_id=parent.id,
        person2_id=child.id,
        rel_type="parent_child",
        confidence=match.confidence_score,
        source=match.source_name,
    ))

    await session.flush()
    return parent.id


def _most_common(items: list[str]) -> str:
    """Return the most common item in a list (simple majority vote)."""
    counts: dict[str, int] = {}
    for item in items:
        normalized = item.strip().lower()
        counts[normalized] = counts.get(normalized, 0) + 1
    best = max(counts, key=counts.get)
    # Return the original-cased version
    for item in items:
        if item.strip().lower() == best:
            return item
    return items[0]
