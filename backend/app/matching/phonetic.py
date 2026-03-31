"""Phonetic matching using Double Metaphone and Soundex."""

import jellyfish

from .normalization import strip_diacritics


def metaphone_match(name_a: str, name_b: str) -> bool:
    """Check if two names share a Metaphone encoding."""
    a = strip_diacritics(name_a)
    b = strip_diacritics(name_b)
    if not a or not b:
        return False
    code_a = jellyfish.metaphone(a)
    code_b = jellyfish.metaphone(b)
    return code_a == code_b


def soundex_match(name_a: str, name_b: str) -> bool:
    """Check if two names share a Soundex encoding."""
    a = strip_diacritics(name_a)
    b = strip_diacritics(name_b)
    if not a or not b:
        return False
    return jellyfish.soundex(a) == jellyfish.soundex(b)
