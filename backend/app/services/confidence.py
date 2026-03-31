"""Confidence scoring engine for genealogical record matching.

Computes a weighted score (0.0-1.0) across multiple factors to determine
how likely a source record matches a known person.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from ..matching.engine import match_given_names, match_surnames
from ..matching.normalization import normalize_place

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

# Source reliability scores
SOURCE_RELIABILITY = {
    "familysearch": 1.0,
    "geneteka": 0.9,
    "szukajwarchiwach": 0.85,
    "ancestry": 0.85,
    "myheritage": 0.8,
    "findagrave": 0.8,
    "billiongraves": 0.75,
    "ellisisland": 0.8,
}


@dataclass
class PersonData:
    """Simplified person data for scoring."""
    given_name: str | None = None
    surname: str | None = None
    birth_year: int | None = None
    birth_place: str | None = None
    death_year: int | None = None
    death_place: str | None = None
    father_given_name: str | None = None
    mother_given_name: str | None = None


def score_birth_year(year_a: int | None, year_b: int | None) -> float:
    """Score birth year match with linear decay."""
    if year_a is None or year_b is None:
        return 0.5  # Unknown = neutral, not penalized
    diff = abs(year_a - year_b)
    if diff == 0:
        return 1.0
    if diff <= 2:
        return 0.9  # Common off-by-one in records
    if diff <= 5:
        return 0.7
    # Linear decay: 0.05 per year, floor at 0
    return max(0.0, 1.0 - diff * 0.05)


def score_place(place_a: str | None, place_b: str | None) -> float:
    """Score place name match."""
    if not place_a or not place_b:
        return 0.5  # Unknown = neutral

    norm_a = normalize_place(place_a)
    norm_b = normalize_place(place_b)

    if norm_a == norm_b:
        return 1.0

    # Check if one contains the other (e.g., "Warszawa" in "Warszawa, Mazowieckie")
    if norm_a in norm_b or norm_b in norm_a:
        return 0.85

    # Check for shared tokens (e.g., same city but different formatting)
    tokens_a = set(norm_a.split())
    tokens_b = set(norm_b.split())
    if tokens_a and tokens_b:
        overlap = tokens_a & tokens_b
        if overlap:
            return 0.6 + 0.3 * (len(overlap) / max(len(tokens_a), len(tokens_b)))

    return 0.0


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

    # Birth year
    year_score = score_birth_year(known.birth_year, candidate.birth_year)
    breakdown["birth_year"] = round(year_score, 3)

    # Birth place
    place_score = score_place(known.birth_place, candidate.birth_place)
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

    # Source reliability
    reliability = SOURCE_RELIABILITY.get(source_name, 0.7)
    breakdown["source_reliability"] = reliability

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
