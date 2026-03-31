"""MyHeritage search adapter.

MyHeritage has a massive record collection including census, immigration,
military, and vital records. Uses their public search which returns
SuperSearch results without requiring API keys.
"""

from __future__ import annotations

import logging
import re

import httpx
from selectolax.parser import HTMLParser

from .base import SourceRecord

logger = logging.getLogger(__name__)

MH_SEARCH_URL = "https://www.myheritage.com/research"


class MyHeritageSource:
    name = "myheritage"

    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9,pl;q=0.8",
            },
            follow_redirects=True,
        )

    async def search_person(
        self,
        given_name: str | None = None,
        surname: str | None = None,
        birth_year: int | None = None,
        birth_place: str | None = None,
        death_year: int | None = None,
        father_given_name: str | None = None,
        father_surname: str | None = None,
        mother_given_name: str | None = None,
        mother_surname: str | None = None,
    ) -> list[SourceRecord]:
        if not surname:
            return []

        # Build the SuperSearch query params
        params: dict[str, str] = {
            "action": "query",
            "qname": f"Name fnmo.{given_name or ''} lnmo.{surname}",
        }

        if birth_year:
            params["qname"] += f" Birth+Year by.{birth_year} byr.5"
        if birth_place:
            params["qname"] += f" Birth+Place bp.{birth_place}"
        if death_year:
            params["qname"] += f" Death+Year dy.{death_year} dyr.5"
        if father_given_name:
            params["qname"] += f" Father+First+Name ffn.{father_given_name}"
        if mother_given_name:
            params["qname"] += f" Mother+First+Name mfn.{mother_given_name}"

        try:
            resp = await self._client.get(MH_SEARCH_URL, params=params)
            resp.raise_for_status()
            results = self._parse_results(resp.text)
            logger.info(
                "MyHeritage returned %d results for %s %s",
                len(results), given_name, surname,
            )
            return results
        except Exception as e:
            logger.error("MyHeritage search failed: %s", e)
            return []

    def _parse_results(self, html: str) -> list[SourceRecord]:
        tree = HTMLParser(html)
        results = []

        # MyHeritage SuperSearch result cards
        cards = tree.css(
            "div.record_item, div.result_item, "
            "div.search-result-card, tr.record-row, "
            "div[class*='SearchResult'], li.result"
        )

        for card in cards[:50]:
            record = self._parse_card(card)
            if record:
                results.append(record)

        return results

    def _parse_card(self, card) -> SourceRecord | None:
        # Find link with record ID
        link = card.css_first("a[href*='/record-'], a[href*='recordId='], a.record-link")
        if not link:
            link = card.css_first("a[href]")
        if not link:
            return None

        href = link.attributes.get("href", "")
        if not href:
            return None

        # Extract record ID
        id_match = re.search(r"record[_-](\d+-\d+-\d+)|recordId=(\d+)", href)
        record_id = id_match.group(1) or id_match.group(2) if id_match else href[-20:]

        if not href.startswith("http"):
            href = f"https://www.myheritage.com{href}"

        # Extract name
        name_el = card.css_first("span.record_name, .result-name, h3 a, h4 a, a.name")
        full_name = name_el.text(strip=True) if name_el else link.text(strip=True)

        parts = full_name.split()
        given_name = parts[0] if parts else None
        surname = parts[-1] if len(parts) > 1 else None

        # Extract details from card
        card_text = card.text(strip=True)

        # Extract birth/death info
        birth_year = None
        death_year = None
        birth_place = None

        # Pattern: "born YYYY in PLACE"
        born_match = re.search(
            r"(?:born|ur\.?|b\.?)\s+(?:(?:abt|circa|ok\.?|ca\.?)?\s*)?(\d{4})\s*(?:in|w|,)\s*([\w\s,]+?)(?:\s*[-;.]|\s*died|\s*zm|\s*d\.)",
            card_text, re.IGNORECASE,
        )
        if born_match:
            birth_year = int(born_match.group(1))
            birth_place = born_match.group(2).strip()
        else:
            # Just year pattern
            years = re.findall(r"\b(1[5-9]\d{2}|20[0-2]\d)\b", card_text)
            if years:
                birth_year = int(years[0])
                if len(years) > 1:
                    death_year = int(years[1])

        # Death year
        died_match = re.search(r"(?:died|zm\.?|d\.?)\s+(?:abt\s+)?(\d{4})", card_text, re.IGNORECASE)
        if died_match:
            death_year = int(died_match.group(1))

        # Residence/place
        place_match = re.search(r"(?:residence|mieszka|living in|from)\s*:?\s*([\w\s,]+?)(?:\s*[-;.]|$)", card_text, re.IGNORECASE)
        if place_match and not birth_place:
            birth_place = place_match.group(1).strip()

        # Record type (collection name)
        collection_el = card.css_first(".collection-name, .record-type, .source-name, small")
        collection = collection_el.text(strip=True) if collection_el else None

        # Family members
        father_name = None
        mother_name = None
        father_match = re.search(r"(?:father|ojciec)\s*:?\s*([\w\s]+?)(?:[,;.]|$)", card_text, re.IGNORECASE)
        if father_match:
            father_name = father_match.group(1).strip()
        mother_match = re.search(r"(?:mother|matka)\s*:?\s*([\w\s]+?)(?:[,;.]|$)", card_text, re.IGNORECASE)
        if mother_match:
            mother_name = mother_match.group(1).strip()

        return SourceRecord(
            source_name=self.name,
            source_record_id=f"mh-{record_id}",
            source_url=href,
            given_name=given_name,
            surname=surname,
            birth_year=birth_year,
            birth_date=str(birth_year) if birth_year else None,
            birth_place=birth_place,
            death_year=death_year,
            death_date=str(death_year) if death_year else None,
            father_name=father_name,
            mother_name=mother_name,
            raw_data={
                "full_name": full_name,
                "collection": collection,
                "card_text": card_text[:300],
            },
        )

    async def get_record_detail(self, record_id: str) -> SourceRecord | None:
        # MyHeritage record detail pages require authentication for full details
        return None
