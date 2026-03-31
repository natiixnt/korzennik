"""GEDCOM 5.5.1 import/export service."""

from __future__ import annotations

import re
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Person, PersonEvent, PersonName, Relationship


async def import_gedcom(session: AsyncSession, text: str) -> int:
    """Parse GEDCOM text and create Person/Relationship records.

    Returns the number of persons imported.
    """
    lines = text.strip().split("\n")
    persons_data: dict[str, dict] = {}  # GEDCOM INDI tag -> data
    families_data: dict[str, dict] = {}  # GEDCOM FAM tag -> data
    current_record = None
    current_tag = None
    current_event = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split(None, 2)
        level = int(parts[0])
        tag = parts[1] if len(parts) > 1 else ""
        value = parts[2] if len(parts) > 2 else ""

        # Level 0: new record
        if level == 0:
            current_event = None
            if tag.startswith("@") and len(parts) > 2:
                record_id = tag
                record_type = value
                if record_type == "INDI":
                    current_record = {"id": record_id, "names": [], "events": [], "gender": None}
                    persons_data[record_id] = current_record
                    current_tag = "INDI"
                elif record_type == "FAM":
                    current_record = {"id": record_id, "husb": None, "wife": None, "children": []}
                    families_data[record_id] = current_record
                    current_tag = "FAM"
                else:
                    current_record = None
                    current_tag = None
            else:
                current_record = None
                current_tag = None
            continue

        if current_record is None:
            continue

        # INDI record fields
        if current_tag == "INDI":
            if level == 1:
                current_event = None
                if tag == "NAME":
                    # Parse "Given /Surname/"
                    match = re.match(r"(.+?)\s*/(.+?)/", value)
                    if match:
                        current_record["names"].append({
                            "given": match.group(1).strip(),
                            "surname": match.group(2).strip(),
                        })
                    else:
                        current_record["names"].append({"given": value.strip("/").strip(), "surname": None})
                elif tag == "SEX":
                    current_record["gender"] = value.strip()
                elif tag in ("BIRT", "DEAT", "IMMI", "EMIG", "RESI"):
                    event_map = {"BIRT": "birth", "DEAT": "death", "IMMI": "immigration", "EMIG": "emigration", "RESI": "residence"}
                    current_event = {"type": event_map.get(tag, tag.lower()), "date": None, "place": None}
                    current_record["events"].append(current_event)
            elif level == 2 and current_event:
                if tag == "DATE":
                    current_event["date"] = value
                elif tag == "PLAC":
                    current_event["place"] = value

        # FAM record fields
        elif current_tag == "FAM":
            if level == 1:
                if tag == "HUSB":
                    current_record["husb"] = value
                elif tag == "WIFE":
                    current_record["wife"] = value
                elif tag == "CHIL":
                    current_record["children"].append(value)

    # Create Person records
    gedcom_to_db_id: dict[str, str] = {}
    count = 0

    for gedcom_id, data in persons_data.items():
        person = Person(
            gender=data.get("gender"),
            origin="gedcom_import",
        )
        session.add(person)
        await session.flush()
        gedcom_to_db_id[gedcom_id] = person.id

        for i, name_data in enumerate(data.get("names", [])):
            session.add(PersonName(
                person_id=person.id,
                given_name=name_data.get("given"),
                surname=name_data.get("surname"),
                name_type="birth" if i == 0 else "also_known_as",
                is_primary=(i == 0),
            ))

        for event_data in data.get("events", []):
            year = None
            date_text = event_data.get("date")
            if date_text:
                year_match = re.search(r"(\d{4})", date_text)
                if year_match:
                    year = int(year_match.group(1))

            session.add(PersonEvent(
                person_id=person.id,
                event_type=event_data["type"],
                date_text=date_text,
                date_year=year,
                place_text=event_data.get("place"),
            ))

        count += 1

    # Create Relationships from FAM records
    for fam_data in families_data.values():
        husb_id = gedcom_to_db_id.get(fam_data.get("husb", ""))
        wife_id = gedcom_to_db_id.get(fam_data.get("wife", ""))

        # Spouse relationship
        if husb_id and wife_id:
            session.add(Relationship(
                person1_id=husb_id,
                person2_id=wife_id,
                rel_type="spouse",
                source="gedcom_import",
            ))

        # Parent-child relationships
        for child_ref in fam_data.get("children", []):
            child_id = gedcom_to_db_id.get(child_ref)
            if child_id:
                if husb_id:
                    session.add(Relationship(
                        person1_id=husb_id,
                        person2_id=child_id,
                        rel_type="parent_child",
                        source="gedcom_import",
                    ))
                if wife_id:
                    session.add(Relationship(
                        person1_id=wife_id,
                        person2_id=child_id,
                        rel_type="parent_child",
                        source="gedcom_import",
                    ))

    await session.commit()
    return count


def _format_gedcom_date(date_text: str | None) -> str:
    """Format a date for GEDCOM output."""
    if not date_text:
        return ""
    return date_text.upper()


async def export_gedcom(session: AsyncSession) -> str:
    """Export all persons and relationships as GEDCOM 5.5.1 text."""
    # Load all data
    stmt = select(Person).options(
        selectinload(Person.names), selectinload(Person.events)
    )
    result = await session.execute(stmt)
    persons = result.scalars().all()

    rel_stmt = select(Relationship)
    rel_result = await session.execute(rel_stmt)
    relationships = rel_result.scalars().all()

    # Build GEDCOM
    lines = [
        "0 HEAD",
        "1 SOUR Korzennik",
        "2 VERS 0.1.0",
        "1 GEDC",
        "2 VERS 5.5.1",
        "2 FORM LINEAGE-LINKED",
        "1 CHAR UTF-8",
    ]

    # Person ID -> GEDCOM INDI tag mapping
    id_to_tag = {}
    for i, person in enumerate(persons, 1):
        tag = f"@I{i}@"
        id_to_tag[person.id] = tag

    # INDI records
    for person in persons:
        tag = id_to_tag[person.id]
        lines.append(f"0 {tag} INDI")

        for name in person.names:
            given = name.given_name or ""
            surname = name.surname or ""
            lines.append(f"1 NAME {given} /{surname}/")

        if person.gender:
            lines.append(f"1 SEX {person.gender}")

        event_tags = {
            "birth": "BIRT", "death": "DEAT",
            "immigration": "IMMI", "emigration": "EMIG",
            "residence": "RESI",
        }
        for event in person.events:
            gedcom_tag = event_tags.get(event.event_type, event.event_type.upper()[:4])
            lines.append(f"1 {gedcom_tag}")
            if event.date_text:
                lines.append(f"2 DATE {_format_gedcom_date(event.date_text)}")
            if event.place_text:
                lines.append(f"2 PLAC {event.place_text}")

    # Build FAM records from relationships
    # Group spouse pairs and their children
    spouse_pairs: dict[tuple[str, str], list[str]] = {}
    parent_child_rels = [r for r in relationships if r.rel_type == "parent_child"]
    spouse_rels = [r for r in relationships if r.rel_type == "spouse"]

    fam_counter = 1
    fam_lines = []

    for sr in spouse_rels:
        pair = (sr.person1_id, sr.person2_id)
        if pair not in spouse_pairs:
            spouse_pairs[pair] = []

    # Find children for each spouse pair
    for pair, children in spouse_pairs.items():
        for pcr in parent_child_rels:
            if pcr.person1_id in pair:
                if pcr.person2_id not in children:
                    children.append(pcr.person2_id)

    for (p1, p2), children in spouse_pairs.items():
        fam_tag = f"@F{fam_counter}@"
        fam_counter += 1
        fam_lines.append(f"0 {fam_tag} FAM")
        if p1 in id_to_tag:
            fam_lines.append(f"1 HUSB {id_to_tag[p1]}")
        if p2 in id_to_tag:
            fam_lines.append(f"1 WIFE {id_to_tag[p2]}")
        for child_id in children:
            if child_id in id_to_tag:
                fam_lines.append(f"1 CHIL {id_to_tag[child_id]}")

    lines.extend(fam_lines)
    lines.append("0 TRLR")

    return "\n".join(lines) + "\n"
