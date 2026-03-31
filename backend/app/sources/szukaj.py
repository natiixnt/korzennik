"""szukajwarchiwach.gov.pl scraper adapter.

Polish National Archives search portal. Contains digitized parish records,
civil records, census data, and other archival materials.
"""

from __future__ import annotations

import asyncio
import logging
import re

import httpx
from selectolax.parser import HTMLParser

from ..config import settings
from .base import SourceRecord

logger = logging.getLogger(__name__)

SZUKAJ_BASE = "https://szukajwarchiwach.gov.pl"
SZUKAJ_SEARCH = f"{SZUKAJ_BASE}/search"


class SzukajWArchiwachSource:
    name = "szukajwarchiwach"

    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
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

        # Build search query - szukajwarchiwach uses full-text search
        query_parts = []
        if given_name:
            query_parts.append(given_name)
        query_parts.append(surname)
        if birth_place:
            query_parts.append(birth_place)

        query = " ".join(query_parts)

        params = {
            "q": query,
            "page": "1",
        }
        if birth_year:
            params["date_from"] = str(birth_year - 5)
            params["date_to"] = str(birth_year + 10)

        try:
            resp = await self._client.get(SZUKAJ_SEARCH, params=params)
            resp.raise_for_status()
            results = self._parse_results(resp.text, surname, given_name)
            logger.info(
                "szukajwarchiwach returned %d results for %s %s",
                len(results), given_name, surname,
            )
            return results
        except Exception as e:
            logger.error("szukajwarchiwach search failed: %s", e)
            return []

    def _parse_results(self, html: str, surname: str, given_name: str | None) -> list[SourceRecord]:
        tree = HTMLParser(html)
        results = []

        # Parse search result items
        items = tree.css("div.result-item, div.search-result, article.result, li.result-item")
        if not items:
            # Try broader selectors
            items = tree.css("div.row.result, div[class*='result']")

        for item in items[:50]:
            try:
                record = self._parse_result_item(item, surname, given_name)
                if record:
                    results.append(record)
            except Exception as e:
                logger.debug("Failed to parse szukajwarchiwach result: %s", e)

        return results

    def _parse_result_item(self, item, surname: str, given_name: str | None) -> SourceRecord | None:
        # Get the link to the full record
        link = item.css_first("a[href]")
        if not link:
            return None

        href = link.attributes.get("href", "")
        if not href:
            return None

        # Extract record ID from URL
        match = re.search(r"/(\d+)/?$", href)
        record_id = match.group(1) if match else href.replace("/", "_")

        if not href.startswith("http"):
            href = f"{SZUKAJ_BASE}{href}"

        # Get title/description text
        title_el = item.css_first("h3, h4, .result-title, .title, a")
        title = title_el.text(strip=True) if title_el else ""

        desc_el = item.css_first("p, .result-description, .description, .snippet")
        description = desc_el.text(strip=True) if desc_el else ""

        full_text = f"{title} {description}"

        # Try to extract date range from the record
        year_match = re.findall(r"\b(1[5-9]\d{2}|20[0-2]\d)\b", full_text)
        birth_year = None
        if year_match:
            # Use the earliest year as approximate birth year
            years = sorted(set(int(y) for y in year_match))
            birth_year = years[0]

        # Extract place from description
        place = None
        # Common patterns: "parafia X", "gmina X", "powiat X"
        place_match = re.search(
            r"(?:parafia|par\.|gmina|gm\.|powiat|pow\.|miasto)\s+(\w[\w\s]*?)(?:[,;.]|$)",
            full_text, re.IGNORECASE,
        )
        if place_match:
            place = place_match.group(1).strip()

        # Determine event type from title/description
        event_type = None
        text_lower = full_text.lower()
        if any(w in text_lower for w in ["urodzen", "chrzest", "chrzt", "natus", "baptism"]):
            event_type = "birth"
        elif any(w in text_lower for w in ["zgon", "smierc", "pogrzeb", "defunctorum", "death"]):
            event_type = "death"
        elif any(w in text_lower for w in ["slub", "malzen", "matrimonium", "marriage"]):
            event_type = "marriage"

        # Try to extract parent names from description
        father_name = None
        mother_name = None
        father_match = re.search(
            r"(?:ojciec|ojca|father|pater)\s*:?\s*(\w+(?:\s+\w+)?)",
            full_text, re.IGNORECASE,
        )
        if father_match:
            father_name = father_match.group(1)
        mother_match = re.search(
            r"(?:matka|matki|mother|mater)\s*:?\s*(\w+(?:\s+\w+)?)",
            full_text, re.IGNORECASE,
        )
        if mother_match:
            mother_name = mother_match.group(1)

        record = SourceRecord(
            source_name=self.name,
            source_record_id=f"swa-{record_id}",
            source_url=href,
            given_name=given_name,
            surname=surname,
            birth_year=birth_year,
            birth_date=str(birth_year) if birth_year else None,
            birth_place=place,
            event_type=event_type,
            father_name=father_name,
            mother_name=mother_name,
            raw_data={
                "title": title,
                "description": description,
                "event_type": event_type,
            },
        )

        return record

    async def get_record_detail(self, record_id: str) -> SourceRecord | None:
        swa_id = record_id.replace("swa-", "")
        url = f"{SZUKAJ_BASE}/{swa_id}"

        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
        except Exception:
            return None

        tree = HTMLParser(resp.text)
        title_el = tree.css_first("h1, .unit-title")
        title = title_el.text(strip=True) if title_el else ""

        desc_el = tree.css_first(".unit-description, .description, article")
        description = desc_el.text(strip=True) if desc_el else ""

        full_text = f"{title} {description}"
        years = re.findall(r"\b(1[5-9]\d{2}|20[0-2]\d)\b", full_text)

        return SourceRecord(
            source_name=self.name,
            source_record_id=record_id,
            source_url=url,
            birth_year=int(years[0]) if years else None,
            raw_data={"title": title, "description": description},
        )
