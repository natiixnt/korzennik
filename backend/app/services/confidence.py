"""Confidence scoring engine for genealogical record matching.

Computes a weighted score (0.0-1.0) across multiple factors to determine
how likely a source record matches a known person.

Features:
- Polish name matching (gender variants, Latin church forms, phonetics)
- Historical place name equivalences (Breslau=Wroclaw, Lemberg=Lwow)
- Enhanced date parsing (approximate, ranges, Polish/Latin formats)
- Record-type-aware scoring (birth record > census > grave)
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from ..matching.date_parser import ParsedDate, parse_date, score_dates
from ..matching.engine import match_given_names, match_surnames
from ..matching.places import places_match

# Weights for each scoring factor (must sum to 1.0)
WEIGHTS = {
    "surname": 0.25,
    "given_name": 0.20,
    "birth_year": 0.15,
    "birth_place": 0.15,
    "father_name": 0.10,
    "mother_name": 0.10,
    "source_reliability": 0.05,
}

# Base source reliability scores
SOURCE_RELIABILITY = {
    "familysearch": 1.0,
    "geneteka": 0.9,
    "metryki": 0.9,
    "poznan_project": 0.9,
    "jri_poland": 0.9,
    "szukajwarchiwach": 0.85,
    "ancestry": 0.85,
    "yad_vashem": 0.85,
    "myheritage": 0.8,
    "findagrave": 0.8,
    "ellisisland": 0.8,
    "castle_garden": 0.8,
    "wikitree": 0.8,
    "geneanet": 0.75,
    "billiongraves": 0.75,
    "matricula": 0.85,
}

# Record type reliability multipliers
# Applied on top of source reliability to reflect how authoritative
# the specific record type is for the data it contains
RECORD_TYPE_MULTIPLIER = {
    "birth": 1.0,       # Birth certificate: authoritative for name, parents, birth date
    "marriage": 0.95,    # Marriage record: names both sets of parents
    "death": 0.90,       # Death record: authoritative for death info, less for birth
    "baptism": 0.95,     # Church baptism: similar to birth record
    "census": 0.75,      # Census: good for name/place, approximate dates
    "grave": 0.70,       # Headstone: dates may be inaccurate
    "immigration": 0.80, # Manifest: names often misspelled by clerks
    "emigration": 0.80,
    "military": 0.80,
    "tree": 0.60,        # User-contributed tree: unverified
    "index": 0.85,       # Index entry (like Geneteka): professionally indexed
}


@dataclass
class PersonData:
    """Simplified person data for scoring."""
    given_name: str | None = None
    surname: str | None = None
    birth_year: int | None = None
    birth_date_text: str | None = None
    birth_place: str | None = None
    death_year: int | None = None
    death_date_text: str | None = None
    death_place: str | None = None
    father_given_name: str | None = None
    mother_given_name: str | None = None
    record_type: str | None = None  # birth, death, marriage, census, grave, etc.


def compute_confidence(
    known: PersonData,
    candidate: PersonData,
    source_name: str,
) -> tuple[float, dict]:
    """Compute confidence score and breakdown for a candidate match.

    Returns (total_score, breakdown_dict).
    """
    breakdown = {}

    # Surname
    surname_score = match_surnames(known.surname or "", candidate.surname or "")
    breakdown["surname"] = round(surname_score, 3)

    # Given name
    given_score = match_given_names(known.given_name or "", candidate.given_name or "")
    breakdown["given_name"] = round(given_score, 3)

    # Birth year - use enhanced date parser
    date_a = parse_date(known.birth_date_text) if known.birth_date_text else ParsedDate(year=known.birth_year)
    date_b = parse_date(candidate.birth_date_text) if candidate.birth_date_text else ParsedDate(year=candidate.birth_year)
    year_score = score_dates(date_a, date_b)
    breakdown["birth_year"] = round(year_score, 3)

    # Birth place - use historical place name matching
    place_score = places_match(known.birth_place or "", candidate.birth_place or "")
    breakdown["birth_place"] = round(place_score, 3)

    # Father's given name
    father_score = match_given_names(
        known.father_given_name or "", candidate.father_given_name or ""
    )
    breakdown["father_name"] = round(father_score, 3)

    # Mother's given name
    mother_score = match_given_names(
        known.mother_given_name or "", candidate.mother_given_name or ""
    )
    breakdown["mother_name"] = round(mother_score, 3)

    # Source reliability (base * record type multiplier)
    base_reliability = SOURCE_RELIABILITY.get(source_name, 0.7)
    record_multiplier = RECORD_TYPE_MULTIPLIER.get(
        candidate.record_type or "", 0.85
    )
    reliability = base_reliability * record_multiplier
    breakdown["source_reliability"] = round(reliability, 3)
    breakdown["record_type"] = candidate.record_type or "unknown"

    # Weighted total
    total = (
        WEIGHTS["surname"] * surname_score
        + WEIGHTS["given_name"] * given_score
        + WEIGHTS["birth_year"] * year_score
        + WEIGHTS["birth_place"] * place_score
        + WEIGHTS["father_name"] * father_score
        + WEIGHTS["mother_name"] * mother_score
        + WEIGHTS["source_reliability"] * reliability
    )

    breakdown["total"] = round(total, 3)
    return total, breakdown
