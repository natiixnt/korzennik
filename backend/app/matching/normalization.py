"""Name normalization utilities for genealogical matching."""

import re
import unicodedata

from unidecode import unidecode

# Polish diacritics mapping (preserves more info than full unidecode)
POLISH_DIACRITICS = {
    "a\u0328": "a",  # a ogonek
    "c\u0301": "c",  # c acute
    "e\u0328": "e",  # e ogonek
    "l\u0335": "l",  # l stroke (not standard but sometimes seen)
    "\u0142": "l",   # l with stroke
    "n\u0301": "n",  # n acute
    "o\u0301": "o",  # o acute
    "s\u0301": "s",  # s acute
    "z\u0301": "z",  # z acute
    "z\u0307": "z",  # z dot above
    "\u0105": "a",   # a ogonek (precomposed)
    "\u0107": "c",   # c acute
    "\u0119": "e",   # e ogonek
    "\u0144": "n",   # n acute
    "\u00f3": "o",   # o acute
    "\u015b": "s",   # s acute
    "\u017a": "z",   # z acute
    "\u017c": "z",   # z dot above
}


def strip_diacritics(text: str) -> str:
    """Remove diacritics, with special handling for Polish characters."""
    result = text.lower()
    for char, replacement in POLISH_DIACRITICS.items():
        result = result.replace(char, replacement)
    # Fallback for any remaining diacritics
    return unidecode(result)


def normalize_name(name: str) -> str:
    """Normalize a name for comparison: lowercase, strip diacritics, collapse whitespace."""
    if not name:
        return ""
    result = strip_diacritics(name.strip())
    result = re.sub(r"[^a-z\s]", "", result)
    result = re.sub(r"\s+", " ", result).strip()
    return result


def normalize_place(place: str) -> str:
    """Normalize a place name for comparison."""
    if not place:
        return ""
    result = strip_diacritics(place.strip())
    # Remove common suffixes/prefixes
    result = re.sub(r"\b(pow|gm|woj|par|diec)\b\.?", "", result)
    result = re.sub(r"[^a-z\s,]", "", result)
    result = re.sub(r"\s+", " ", result).strip()
    return result
