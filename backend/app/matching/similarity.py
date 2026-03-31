"""String similarity metrics for name comparison."""

import jellyfish

from .normalization import normalize_name


def jaro_winkler(name_a: str, name_b: str) -> float:
    """Compute Jaro-Winkler similarity between two names.

    Returns 0.0 to 1.0. Best metric for short strings like names.
    """
    a = normalize_name(name_a)
    b = normalize_name(name_b)
    if not a or not b:
        return 0.0
    return jellyfish.jaro_winkler_similarity(a, b)


def levenshtein_ratio(name_a: str, name_b: str) -> float:
    """Compute normalized Levenshtein similarity (1 - distance/max_len)."""
    a = normalize_name(name_a)
    b = normalize_name(name_b)
    if not a or not b:
        return 0.0
    dist = jellyfish.levenshtein_distance(a, b)
    max_len = max(len(a), len(b))
    return 1.0 - (dist / max_len)
