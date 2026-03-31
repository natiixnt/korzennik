"""Enhanced date parsing for genealogical records.

Handles approximate dates, ranges, Polish/Latin/GEDCOM formats,
and carries qualifier information for smarter confidence scoring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Polish month names
_POLISH_MONTHS = {
    "stycznia": 1, "styczeń": 1, "styczen": 1, "sty": 1,
    "lutego": 2, "luty": 2, "lut": 2,
    "marca": 3, "marzec": 3, "mar": 3,
    "kwietnia": 4, "kwiecień": 4, "kwiecien": 4, "kwi": 4,
    "maja": 5, "maj": 5,
    "czerwca": 6, "czerwiec": 6, "cze": 6,
    "lipca": 7, "lipiec": 7, "lip": 7,
    "sierpnia": 8, "sierpień": 8, "sierpien": 8, "sie": 8,
    "września": 9, "wrzesień": 9, "wrzesien": 9, "wrz": 9,
    "października": 10, "październik": 10, "pazdziernik": 10, "paź": 10, "paz": 10,
    "listopada": 11, "listopad": 11, "lis": 11,
    "grudnia": 12, "grudzień": 12, "grudzien": 12, "gru": 12,
}

# Latin month names (from church records)
_LATIN_MONTHS = {
    "januarii": 1, "januarius": 1, "jan": 1,
    "februarii": 2, "februarius": 2, "feb": 2,
    "martii": 3, "martius": 3, "mar": 3,
    "aprilis": 4, "apr": 4,
    "maii": 5, "maius": 5, "mai": 5,
    "junii": 6, "junius": 6, "jun": 6,
    "julii": 7, "julius": 7, "jul": 7,
    "augusti": 8, "augustus": 8, "aug": 8,
    "septembris": 9, "september": 9, "sep": 9, "sept": 9,
    "octobris": 10, "october": 10, "oct": 10,
    "novembris": 11, "november": 11, "nov": 11,
    "decembris": 12, "december": 12, "dec": 12,
}

# English month names
_ENGLISH_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Roman numeral months
_ROMAN_MONTHS = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6,
    "vii": 7, "viii": 8, "ix": 9, "x": 10, "xi": 11, "xii": 12,
}

ALL_MONTHS = {}
ALL_MONTHS.update(_POLISH_MONTHS)
ALL_MONTHS.update(_LATIN_MONTHS)
ALL_MONTHS.update(_ENGLISH_MONTHS)

# Qualifier patterns
_APPROX_PATTERNS = re.compile(
    r"(?:abt\.?|about|circa|ca\.?|ok\.?|okolo|approximately|~)",
    re.IGNORECASE,
)
_BEFORE_PATTERNS = re.compile(
    r"(?:bef\.?|before|przed|vor|ante)",
    re.IGNORECASE,
)
_AFTER_PATTERNS = re.compile(
    r"(?:aft\.?|after|po|nach|post)",
    re.IGNORECASE,
)
_BETWEEN_PATTERN = re.compile(
    r"(?:bet\.?|between|miedzy)\s+(\d{4})\s+(?:and|i|und|-)\s+(\d{4})",
    re.IGNORECASE,
)


@dataclass
class ParsedDate:
    """Parsed genealogical date with qualifier."""
    year: int | None = None
    month: int | None = None
    day: int | None = None
    qualifier: str = "exact"  # exact | approximate | before | after | between
    year_end: int | None = None  # For "between" ranges

    @property
    def is_approximate(self) -> bool:
        return self.qualifier != "exact"

    @property
    def tolerance_years(self) -> int:
        """How many years of tolerance this date implies."""
        if self.qualifier == "exact" and self.month and self.day:
            return 0
        if self.qualifier == "exact":
            return 1  # Year only = +/- 1 tolerance
        if self.qualifier == "approximate":
            return 3
        if self.qualifier in ("before", "after"):
            return 5
        if self.qualifier == "between" and self.year_end:
            return (self.year_end - (self.year or 0)) // 2
        return 2


def parse_date(text: str | None) -> ParsedDate:
    """Parse a date string from genealogical records.

    Handles:
    - "1885", "abt 1885", "~1885", "ca. 1885", "ok. 1885"
    - "bef 1890", "aft 1880", "przed 1890"
    - "bet 1880 and 1890", "between 1880 and 1890"
    - "15 stycznia 1885", "15.01.1885", "15 I 1885"
    - "die 15 Januarii 1885" (Latin church records)
    - GEDCOM: "ABT 1885", "BEF 1890", "BET 1880 AND 1890"
    - "JAN 1885", "1885-01-15"
    """
    if not text:
        return ParsedDate()

    text = text.strip()
    result = ParsedDate()

    # Check for "between" first
    between = _BETWEEN_PATTERN.search(text)
    if between:
        result.year = int(between.group(1))
        result.year_end = int(between.group(2))
        result.qualifier = "between"
        return result

    # Detect qualifier
    if _APPROX_PATTERNS.search(text) or text.startswith("~"):
        result.qualifier = "approximate"
        text = _APPROX_PATTERNS.sub("", text).lstrip("~").strip()
    elif _BEFORE_PATTERNS.search(text):
        result.qualifier = "before"
        text = _BEFORE_PATTERNS.sub("", text).strip()
    elif _AFTER_PATTERNS.search(text):
        result.qualifier = "after"
        text = _AFTER_PATTERNS.sub("", text).strip()

    # Try ISO format: YYYY-MM-DD
    iso = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if iso:
        result.year = int(iso.group(1))
        result.month = int(iso.group(2))
        result.day = int(iso.group(3))
        return result

    # Try DD.MM.YYYY or DD/MM/YYYY
    dmy = re.match(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", text)
    if dmy:
        result.day = int(dmy.group(1))
        result.month = int(dmy.group(2))
        result.year = int(dmy.group(3))
        return result

    # Try "DD MonthName YYYY" or "MonthName DD, YYYY" or "die DD MonthName YYYY"
    text_lower = text.lower()
    # Remove Latin prefix "die"
    text_lower = re.sub(r"^die\s+", "", text_lower)

    # Try "DD month YYYY"
    dm_match = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", text_lower)
    if dm_match:
        result.day = int(dm_match.group(1))
        month_str = dm_match.group(2)
        result.year = int(dm_match.group(3))
        result.month = _lookup_month(month_str)
        return result

    # Try "month DD, YYYY"
    md_match = re.match(r"(\w+)\s+(\d{1,2}),?\s+(\d{4})", text_lower)
    if md_match:
        month_str = md_match.group(1)
        result.day = int(md_match.group(2))
        result.year = int(md_match.group(3))
        result.month = _lookup_month(month_str)
        return result

    # Try "DD RomanMonth YYYY" (e.g., "15 I 1885")
    roman = re.match(r"(\d{1,2})\s+(i{1,3}|iv|v|vi{0,3}|ix|x|xi{0,2})\s+(\d{4})", text_lower)
    if roman:
        result.day = int(roman.group(1))
        result.month = _ROMAN_MONTHS.get(roman.group(2))
        result.year = int(roman.group(3))
        return result

    # Try "month YYYY"
    my_match = re.match(r"(\w+)\s+(\d{4})", text_lower)
    if my_match:
        month = _lookup_month(my_match.group(1))
        if month:
            result.month = month
            result.year = int(my_match.group(2))
            return result

    # Fallback: just extract a year
    year_match = re.search(r"\b(\d{4})\b", text)
    if year_match:
        result.year = int(year_match.group(1))

    return result


def _lookup_month(text: str) -> int | None:
    """Look up a month name in all supported languages."""
    text = text.lower().strip(".")
    return ALL_MONTHS.get(text) or _ROMAN_MONTHS.get(text)


def score_dates(date_a: ParsedDate, date_b: ParsedDate) -> float:
    """Score how well two parsed dates match, considering qualifiers.

    Returns 0.0 to 1.0.
    """
    if date_a.year is None or date_b.year is None:
        return 0.5  # Unknown = neutral

    # For "between" ranges, check overlap
    if date_a.qualifier == "between" and date_a.year_end:
        if date_a.year <= (date_b.year or 0) <= date_a.year_end:
            return 0.9
    if date_b.qualifier == "between" and date_b.year_end:
        if date_b.year <= (date_a.year or 0) <= date_b.year_end:
            return 0.9

    diff = abs(date_a.year - date_b.year)

    # Combine tolerances from both dates
    tolerance = date_a.tolerance_years + date_b.tolerance_years

    if diff == 0:
        # Exact year match - bonus if day/month also match
        if date_a.month and date_b.month and date_a.month == date_b.month:
            if date_a.day and date_b.day and date_a.day == date_b.day:
                return 1.0  # Exact date match
            return 0.98  # Same month
        return 0.95  # Same year

    if diff <= max(2, tolerance):
        return 0.85  # Within tolerance
    if diff <= 5:
        return 0.7
    if diff <= 10:
        return 0.4

    # Linear decay beyond 10 years
    return max(0.0, 0.4 - (diff - 10) * 0.04)
