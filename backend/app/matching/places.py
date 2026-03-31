"""Historical place name normalization for Polish genealogy.

Maps German, Russian, Latin, Yiddish, and modern names to a canonical form.
Handles partition-era name changes, border shifts, and transliteration variants.
"""

from __future__ import annotations

from .normalization import strip_diacritics

# Canonical: modern Polish name (lowercase, no diacritics)
# Maps alternate names -> canonical name
_PLACE_EQUIVALENCES: dict[str, str] = {
    # Major cities - German partition (Prussian)
    "breslau": "wroclaw", "wroclaw": "wroclaw",
    "danzig": "gdansk", "gdansk": "gdansk",
    "posen": "poznan", "poznan": "poznan",
    "stettin": "szczecin", "szczecin": "szczecin",
    "thorn": "torun", "torun": "torun",
    "elbing": "elblag", "elblag": "elblag",
    "allenstein": "olsztyn", "olsztyn": "olsztyn",
    "bromberg": "bydgoszcz", "bydgoszcz": "bydgoszcz",
    "kattowitz": "katowice", "katowice": "katowice",
    "gleiwitz": "gliwice", "gliwice": "gliwice",
    "oppeln": "opole", "opole": "opole",
    "beuthen": "bytom", "bytom": "bytom",
    "hindenburg": "zabrze", "zabrze": "zabrze",
    "konigshütte": "chorzow", "konighutte": "chorzow", "chorzow": "chorzow",
    "grünberg": "zielona gora", "grunberg": "zielona gora", "zielona gora": "zielona gora",
    "landsberg": "gorzow wielkopolski", "gorzow": "gorzow wielkopolski",
    "lauenburg": "lebork", "lebork": "lebork",
    "kolberg": "kolobrzeg", "kolobrzeg": "kolobrzeg",
    "stolp": "slupsk", "slupsk": "slupsk",
    "köslin": "koszalin", "koslin": "koszalin", "koszalin": "koszalin",
    "liegnitz": "legnica", "legnica": "legnica",
    "görlitz": "gorlitz", "zgorzelec": "zgorzelec",
    "waldenburg": "walbrzych", "walbrzych": "walbrzych",
    "schweidnitz": "swidnica", "swidnica": "swidnica",
    "ratibor": "raciborz", "raciborz": "raciborz",
    "neisse": "nysa", "nysa": "nysa",
    "inowrazlaw": "inowroclaw", "inowroclaw": "inowroclaw",
    "gnesen": "gniezno", "gniezno": "gniezno",
    "lissa": "leszno", "leszno": "leszno",
    "meseritz": "miedzyrzecz", "miedzyrzecz": "miedzyrzecz",
    "schneidemühl": "pila", "schneidemuhl": "pila", "pila": "pila",
    "marienwerder": "kwidzyn", "kwidzyn": "kwidzyn",
    "graudenz": "grudziadz", "grudziadz": "grudziadz",
    "kulm": "chelmno", "chelmno": "chelmno",

    # Major cities - Austrian partition (Galicia)
    "lemberg": "lwow", "lwow": "lwow", "lviv": "lwow", "lvov": "lwow",
    "leopolis": "lwow",  # Latin
    "krakau": "krakow", "cracow": "krakow", "krakow": "krakow",
    "cracovia": "krakow",  # Latin
    "tarnopol": "ternopil", "ternopil": "ternopil",
    "stanislau": "ivano-frankivsk", "stanisławow": "ivano-frankivsk",
    "stanislawow": "ivano-frankivsk",
    "przemysl": "przemysl", "przemyśl": "przemysl",
    "rzeszow": "rzeszow", "rzeszów": "rzeszow",
    "nowy sacz": "nowy sacz", "nowy sącz": "nowy sacz", "neu sandez": "nowy sacz",
    "tarnow": "tarnow", "tarnów": "tarnow",
    "jaroslaw": "jaroslaw", "jaroslau": "jaroslaw",
    "krosno": "krosno",
    "sanok": "sanok",
    "drohobycz": "drohobych", "drohobych": "drohobych",
    "sambor": "sambir", "sambir": "sambir",
    "stryj": "stryi", "stryi": "stryi",
    "bochnia": "bochnia",
    "wieliczka": "wieliczka",
    "wadowice": "wadowice",
    "biala": "bielsko-biala", "bielitz": "bielsko-biala", "bielsko": "bielsko-biala",

    # Major cities - Russian partition (Congress Poland)
    "warszawa": "warszawa", "warschau": "warszawa", "warsaw": "warszawa",
    "varsovia": "warszawa",  # Latin
    "varshava": "warszawa",  # Russian transliteration
    "lodz": "lodz", "lodzh": "lodz",
    "lublin": "lublin",
    "radom": "radom",
    "kielce": "kielce",
    "plock": "plock", "plotsk": "plock",
    "siedlce": "siedlce",
    "lomza": "lomza",
    "suwalki": "suwalki",
    "czestochowa": "czestochowa", "tschenstochau": "czestochowa",
    "piotrkow": "piotrkow trybunalski", "petrikau": "piotrkow trybunalski",
    "kalisz": "kalisz", "kalisch": "kalisz",
    "bialystok": "bialystok", "belostok": "bialystok",
    "grodno": "grodno", "hrodna": "grodno",
    "wilno": "wilno", "vilnius": "wilno", "vilna": "wilno",
    "kowno": "kaunas", "kaunas": "kaunas", "kauen": "kaunas",
    "minsk": "minsk",

    # Other important Polish cities
    "gdynia": "gdynia",
    "sopot": "sopot", "zoppot": "sopot",
    "elblag": "elblag",
    "olsztyn": "olsztyn",
    "bialystok": "bialystok",
    "rzeszow": "rzeszow",
    "kielce": "kielce",
    "gorzow wielkopolski": "gorzow wielkopolski",
    "zielona gora": "zielona gora",

    # Common Yiddish/Jewish names for Polish cities
    "varshe": "warszawa",
    "lodzh": "lodz", "lodsch": "lodz",
    "kroke": "krakow",
    "lublin": "lublin",
    "bialystok": "bialystok", "byalistok": "bialystok",
    "radomsk": "radomsko", "radomsko": "radomsko",
    "piotrkow": "piotrkow trybunalski", "petrikow": "piotrkow trybunalski",
    "kieltz": "kielce",
    "plotzk": "plock",
    "lomzhe": "lomza",

    # Countries / regions
    "poland": "polska", "polska": "polska", "polen": "polska",
    "galicia": "galicja", "galicja": "galicja", "galizien": "galicja",
    "congress poland": "krolestwo polskie", "russian poland": "krolestwo polskie",
    "kongresowka": "krolestwo polskie",
    "silesia": "slask", "slask": "slask", "schlesien": "slask",
    "pomerania": "pomorze", "pomorze": "pomorze", "pommern": "pomorze",
    "masuria": "mazury", "mazury": "mazury", "masuren": "mazury",
    "warmia": "warmia", "ermland": "warmia",
    "greater poland": "wielkopolska", "wielkopolska": "wielkopolska",
    "lesser poland": "malopolska", "malopolska": "malopolska",
    "podlasie": "podlasie",
    "volhynia": "wolyn", "wolyn": "wolyn", "wolhynien": "wolyn",
    "podolia": "podole", "podole": "podole",

    # Important emigration destinations
    "new york": "new york", "nowy jork": "new york",
    "chicago": "chicago",
    "detroit": "detroit",
    "pittsburgh": "pittsburgh",
    "cleveland": "cleveland",
    "milwaukee": "milwaukee",
    "buffalo": "buffalo",
    "buenos aires": "buenos aires",
    "sao paulo": "sao paulo",
    "curitiba": "curitiba",
}


def normalize_place_historical(place: str) -> str:
    """Normalize a place name considering historical equivalences.

    Returns the canonical (modern Polish) form if recognized,
    otherwise returns the basic normalized form.
    """
    if not place:
        return ""

    normalized = strip_diacritics(place.strip().lower())

    # Try direct lookup
    canonical = _PLACE_EQUIVALENCES.get(normalized)
    if canonical:
        return canonical

    # Try each word in multi-word places
    words = normalized.split()
    for word in words:
        canonical = _PLACE_EQUIVALENCES.get(word)
        if canonical:
            return canonical

    # Try removing common prefixes/suffixes
    for prefix in ("powiat ", "pow. ", "gmina ", "gm. ", "parafia ", "par. ",
                    "diecezja ", "diec. ", "gubernia ", "gub. ", "kreis ",
                    "bezirk ", "landkreis "):
        if normalized.startswith(prefix):
            rest = normalized[len(prefix):]
            canonical = _PLACE_EQUIVALENCES.get(rest)
            if canonical:
                return canonical

    return normalized


def places_match(place_a: str, place_b: str) -> float:
    """Score how well two place names match, considering historical equivalences.

    Returns 0.0 to 1.0.
    """
    if not place_a or not place_b:
        return 0.5  # Unknown = neutral

    norm_a = normalize_place_historical(place_a)
    norm_b = normalize_place_historical(place_b)

    # Exact canonical match
    if norm_a == norm_b:
        return 1.0

    # One contains the other (e.g., "Warszawa" in "Warszawa, Mazowieckie")
    if norm_a in norm_b or norm_b in norm_a:
        return 0.9

    # Check if they share a canonical city (multi-word comparison)
    tokens_a = set(norm_a.replace(",", " ").split())
    tokens_b = set(norm_b.replace(",", " ").split())

    # Check each token against the equivalence database
    canonical_a = {_PLACE_EQUIVALENCES.get(t, t) for t in tokens_a}
    canonical_b = {_PLACE_EQUIVALENCES.get(t, t) for t in tokens_b}

    overlap = canonical_a & canonical_b
    # Remove very common words
    overlap -= {"polska", "poland", "polen", "powiat", "gmina", "parafia"}

    if overlap:
        significance = len(overlap) / max(len(canonical_a), len(canonical_b))
        return 0.6 + 0.35 * significance

    return 0.0
