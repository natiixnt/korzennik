"""Composite name matching engine combining Polish rules, phonetics, and fuzzy matching."""

from .phonetic import metaphone_match, soundex_match
from .polish import match_given_name_score, match_surname_score
from .similarity import jaro_winkler


def match_surnames(name_a: str, name_b: str) -> float:
    """Match two surnames using a cascade of strategies.

    1. Polish rule-based matching (variants, gender, marital forms)
    2. Phonetic matching (Metaphone/Soundex)
    3. Fuzzy string similarity (Jaro-Winkler)

    Returns 0.0 to 1.0.
    """
    if not name_a or not name_b:
        return 0.0

    # Try Polish rules first
    polish_score = match_surname_score(name_a, name_b)
    if polish_score >= 0.7:
        return polish_score

    # Phonetic matching
    if metaphone_match(name_a, name_b):
        return 0.65
    if soundex_match(name_a, name_b):
        return 0.55

    # Fuzzy similarity as fallback
    jw = jaro_winkler(name_a, name_b)
    if jw >= 0.85:
        return jw * 0.7  # Scale down fuzzy-only matches
    return 0.0


def match_given_names(name_a: str, name_b: str) -> float:
    """Match two given names using Polish rules, phonetics, and fuzzy matching."""
    if not name_a or not name_b:
        return 0.0

    polish_score = match_given_name_score(name_a, name_b)
    if polish_score >= 0.7:
        return polish_score

    if metaphone_match(name_a, name_b):
        return 0.65
    if soundex_match(name_a, name_b):
        return 0.55

    jw = jaro_winkler(name_a, name_b)
    if jw >= 0.85:
        return jw * 0.7
    return 0.0
