"""Polish-specific name variant generation and matching rules.

Handles gender declension, marital forms, patronymics, historical
spelling variations, and Latin church record name mappings.
"""

from .normalization import normalize_name

# Gender variant suffixes for -ski/-cki/-dzki adjective surnames
_ADJECTIVE_ENDINGS = {
    "ski": ["ska", "skie", "skich", "skim"],
    "cki": ["cka", "ckie", "ckich", "ckim"],
    "dzki": ["dzka", "dzkie", "dzkich", "dzkim"],
    "ny": ["na", "ne", "nych", "nym"],
    "wy": ["wa", "we", "wych", "wym"],
}

# Feminine marital forms
# wife: consonant + owa, daughter: consonant + owna/anka
_MARITAL_SUFFIXES_WIFE = ["owa", "ina"]
_MARITAL_SUFFIXES_DAUGHTER = ["owna", "anka"]

# Latin given names -> Polish equivalents (church records)
LATIN_TO_POLISH_GIVEN = {
    "joannes": "jan",
    "johannes": "jan",
    "josephus": "jozef",
    "stanislaus": "stanislaw",
    "andreas": "andrzej",
    "antonius": "antoni",
    "franciscus": "franciszek",
    "jacobus": "jakub",
    "michael": "michal",
    "nicolaus": "mikolaj",
    "petrus": "piotr",
    "paulus": "pawel",
    "thomas": "tomasz",
    "mathias": "maciej",
    "simon": "szymon",
    "bartholomaeus": "bartlomiej",
    "laurentius": "wawrzyniec",
    "valentinus": "walenty",
    "casimirus": "kazimierz",
    "adalbertus": "wojciech",
    "albertus": "wojciech",
    "gregorius": "grzegorz",
    "martinus": "marcin",
    "catharina": "katarzyna",
    "maria": "maria",
    "anna": "anna",
    "helena": "helena",
    "elisabeth": "elzbieta",
    "dorothea": "dorota",
    "margaretha": "malgorzata",
    "sophia": "zofia",
    "agatha": "agata",
    "agnes": "agnieszka",
    "barbara": "barbara",
    "christina": "krystyna",
    "eva": "ewa",
    "lucia": "lucja",
    "magdalena": "magdalena",
    "rosalia": "rozalia",
    "theresia": "teresa",
    "veronica": "weronika",
}

# Build reverse mapping too
POLISH_TO_LATIN_GIVEN: dict[str, list[str]] = {}
for lat, pol in LATIN_TO_POLISH_GIVEN.items():
    POLISH_TO_LATIN_GIVEN.setdefault(pol, []).append(lat)

# Historical spelling variations (German partition influence etc.)
_SPELLING_SWAPS = [
    ("w", "v"),
    ("sz", "sch"),
    ("cz", "tsch"),
    ("rz", "rs"),
    ("rz", "rsch"),
    ("ow", "au"),
    ("ew", "ev"),
    ("j", "y"),
    ("k", "c"),
    ("ks", "x"),
]

# Common Polish given name diminutives
_DIMINUTIVES: dict[str, list[str]] = {
    "jan": ["janek", "jas", "jasiek", "jasio"],
    "jozef": ["jozek", "jozio"],
    "stanislaw": ["staszek", "stas", "stasiek"],
    "andrzej": ["jedrzej", "jedrek"],
    "franciszek": ["franek", "franio"],
    "michal": ["michalek", "misiek"],
    "piotr": ["piotrek", "piotrus"],
    "tomasz": ["tomek", "tomus"],
    "wojciech": ["wojtek", "wojtas"],
    "kazimierz": ["kazik", "kazek"],
    "katarzyna": ["kasia", "kasienka"],
    "maria": ["marysia", "marynia", "mania"],
    "anna": ["ania", "anka", "anusia", "hanna"],
    "zofia": ["zosia", "zosienka"],
    "malgorzata": ["gosia", "gosienka"],
    "elzbieta": ["ela", "elzunia"],
    "magdalena": ["magda", "madzia"],
    "krystyna": ["krysia", "krysienka"],
    "barbara": ["basia", "basienka"],
    "teresa": ["terenia", "tereska"],
}


def generate_surname_variants(surname: str) -> set[str]:
    """Generate all plausible Polish variants of a surname.

    Returns normalized (lowercase, no diacritics) variants.
    """
    if not surname:
        return set()

    base = normalize_name(surname)
    variants = {base}

    # Adjective surname gender variants
    for ending, alts in _ADJECTIVE_ENDINGS.items():
        if base.endswith(ending):
            stem = base[: -len(ending)]
            for alt in alts:
                variants.add(stem + alt)
            break
        for alt in alts:
            if base.endswith(alt):
                variants.add(base[: -len(alt)] + ending)
                # Also generate all other gender forms
                stem = base[: -len(alt)]
                for other_alt in alts:
                    variants.add(stem + other_alt)
                break

    # Marital forms for non-adjective surnames (e.g., Nowak -> Nowakowa, Nowakawna)
    for wife_suf in _MARITAL_SUFFIXES_WIFE:
        if base.endswith(wife_suf):
            # Strip the marital suffix to get base form
            stem = base[: -len(wife_suf)]
            variants.add(stem)
            for d_suf in _MARITAL_SUFFIXES_DAUGHTER:
                variants.add(stem + d_suf)
        else:
            variants.add(base + wife_suf)

    for daughter_suf in _MARITAL_SUFFIXES_DAUGHTER:
        if base.endswith(daughter_suf):
            stem = base[: -len(daughter_suf)]
            variants.add(stem)
            for w_suf in _MARITAL_SUFFIXES_WIFE:
                variants.add(stem + w_suf)

    # Historical spelling swaps
    for orig, swap in _SPELLING_SWAPS:
        if orig in base:
            variants.add(base.replace(orig, swap))
        if swap in base:
            variants.add(base.replace(swap, orig))

    return variants


def generate_given_name_variants(given_name: str) -> set[str]:
    """Generate all plausible variants of a Polish given name.

    Includes Latin church forms, diminutives, and spelling variants.
    """
    if not given_name:
        return set()

    base = normalize_name(given_name)
    variants = {base}

    # Latin <-> Polish mappings
    if base in LATIN_TO_POLISH_GIVEN:
        variants.add(LATIN_TO_POLISH_GIVEN[base])
    if base in POLISH_TO_LATIN_GIVEN:
        variants.update(POLISH_TO_LATIN_GIVEN[base])

    # Diminutives
    if base in _DIMINUTIVES:
        variants.update(_DIMINUTIVES[base])

    # Reverse: if the input is a diminutive, find the formal name
    for formal, dims in _DIMINUTIVES.items():
        if base in dims:
            variants.add(formal)
            variants.update(dims)
            # Also add Latin forms of the formal name
            if formal in POLISH_TO_LATIN_GIVEN:
                variants.update(POLISH_TO_LATIN_GIVEN[formal])

    return variants


def match_surname_score(name_a: str, name_b: str) -> float:
    """Score how well two surnames match, considering Polish rules.

    Returns 0.0 to 1.0.
    """
    if not name_a or not name_b:
        return 0.0

    norm_a = normalize_name(name_a)
    norm_b = normalize_name(name_b)

    if norm_a == norm_b:
        return 1.0

    # Check if b is a known variant of a
    variants_a = generate_surname_variants(name_a)
    if norm_b in variants_a:
        return 0.85

    variants_b = generate_surname_variants(name_b)
    if norm_a in variants_b:
        return 0.85

    # Check overlap of variant sets
    overlap = variants_a & variants_b
    if overlap:
        return 0.7

    return 0.0  # No rule-based match; caller should fall back to phonetic/fuzzy


def infer_base_surname(married_surname: str) -> str | None:
    """Infer the husband's/base surname from a Polish married feminine form.

    E.g., "Nowakowa" -> "Nowak", "Kowalska" -> "Kowalski",
    "Wisniewska" -> "Wisniewski", "Nowakawna" -> "Nowak".

    Returns the base form or None if no marital suffix detected.
    """
    if not married_surname:
        return None

    base = normalize_name(married_surname)

    # Strip marital suffixes (wife: -owa/-ina, daughter: -owna/-anka)
    for suffix in ("owna", "anka", "owa", "ina"):
        if base.endswith(suffix) and len(base) > len(suffix) + 2:
            return base[:-len(suffix)]

    # Strip adjective feminine endings -> masculine
    for fem, masc in [("ska", "ski"), ("cka", "cki"), ("dzka", "dzki"),
                      ("na", "ny"), ("wa", "wy")]:
        if base.endswith(fem) and len(base) > len(fem) + 2:
            return base[:-len(fem)] + masc

    return None


def match_given_name_score(name_a: str, name_b: str) -> float:
    """Score how well two given names match, considering Polish rules.

    Returns 0.0 to 1.0.
    """
    if not name_a or not name_b:
        return 0.0

    norm_a = normalize_name(name_a)
    norm_b = normalize_name(name_b)

    if norm_a == norm_b:
        return 1.0

    variants_a = generate_given_name_variants(name_a)
    if norm_b in variants_a:
        return 0.85

    variants_b = generate_given_name_variants(name_b)
    if norm_a in variants_b:
        return 0.85

    overlap = variants_a & variants_b
    if overlap:
        return 0.7

    return 0.0
