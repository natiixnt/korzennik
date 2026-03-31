"""Ancestry public record search adapter.

Searches Ancestry's publicly available record previews and collections.
Full records require an Ancestry subscription, but search results and
record summaries are publicly accessible.
"""

from __future__ import annotations

import logging
import re

import httpx
from selectolax.parser import HTMLParser

from .base import SourceRecord

logger = logging.getLogger(__name__)

ANCESTRY_SEARCH_URL = "https://www.ancestry.com/search/"


class AncestrySource:
    name = "ancestry"

    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
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

        # Build Ancestry search URL with their query format
        params: dict[str, str] = {
            "name": f"{given_name or ''} {surname}".strip(),
            "name_x": "1",  # Exact match off
        }

        if birth_year:
            params["birth"] = str(birth_year)
            params["birth_x"] = "5"  # +/- range
        if birth_place:
            params["birth_loc"] = birth_place
        if death_year:
            params["death"] = str(death_year)
            params["death_x"] = "5"
        if father_given_name:
            params["father_fn"] = father_given_name
        if father_surname:
            params["father_ln"] = father_surname
        if mother_given_name:
            params["mother_fn"] = mother_given_name
        if mother_surname:
            params["mother_ln"] = mother_surname

        try:
            resp = await self._client.get(ANCESTRY_SEARCH_URL, params=params)
            resp.raise_for_status()
            results = self._parse_results(resp.text)
            logger.info("Ancestry returned %d results for %s %s", len(results), given_name, surname)
            return results
        except Exception as e:
            logger.error("Ancestry search failed: %s", e)
            return []

    def _parse_results(self, html: str) -> list[SourceRecord]:
        tree = HTMLParser(html)
        results = []

        # Ancestry search results use various containers
        cards = tree.css(
            "div.result, div.srchRslt, tr.record, "
            "div[class*='searchResult'], li.result-card, "
            "div.card.result"
        )

        for card in cards[:50]:
            record = self._parse_card(card)
            if record:
                results.append(record)

        return results

    def _parse_card(self, card) -> SourceRecord | None:
        link = card.css_first("a[href*='/discoveryui-content/'], a[href*='dbid='], a.result-title")
        if not link:
            link = card.css_first("a[href]")
        if not link:
            return None

        href = link.attributes.get("href", "")
        if not href:
            return None

        # Extract a record ID
        id_match = re.search(r"pid=(\d+)|dbid=(\d+)&h=(\d+)", href)
        if id_match:
            record_id = id_match.group(1) or f"{id_match.group(2)}-{id_match.group(3)}"
        else:
            record_id = re.sub(r"[^a-zA-Z0-9]", "", href[-30:])

        if not href.startswith("http"):
            href = f"https://www.ancestry.com{href}"

        # Name extraction
        name_el = card.css_first(".srchRsltName, .result-name, h4, h3, a.name")
        full_name = name_el.text(strip=True) if name_el else link.text(strip=True)
        parts = full_name.split()
        given = parts[0] if parts else None
        surname = parts[-1] if len(parts) > 1 else None

        card_text = card.text(strip=True)

        # Extract data fields
        birth_year = None
        death_year = None
        birth_place = None
        death_place = None
        father_name = None
        mother_name = None

        # Look for labeled fields in the result
        fields = self._extract_fields(card)

        if "birth" in fields:
            year_m = re.search(r"(\d{4})", fields["birth"])
            if year_m:
                birth_year = int(year_m.group(1))
        if "birth place" in fields or "birthplace" in fields:
            birth_place = fields.get("birth place", fields.get("birthplace"))
        if "death" in fields:
            year_m = re.search(r"(\d{4})", fields["death"])
            if year_m:
                death_year = int(year_m.group(1))
        if "death place" in fields:
            death_place = fields["death place"]
        if "father" in fields:
            father_name = fields["father"]
        if "mother" in fields:
            mother_name = fields["mother"]

        # Fallback year extraction
        if not birth_year:
            years = re.findall(r"\b(1[5-9]\d{2}|20[0-2]\d)\b", card_text)
            if years:
                birth_year = int(years[0])
                if len(years) > 1 and not death_year:
                    death_year = int(years[1])

        # Collection/record type
        collection_el = card.css_first(".srchRsltCollName, .collection, .source, small.db")
        collection = collection_el.text(strip=True) if collection_el else None

        return SourceRecord(
            source_name=self.name,
            source_record_id=f"anc-{record_id}",
            source_url=href,
            given_name=given,
            surname=surname,
            birth_year=birth_year,
            birth_date=str(birth_year) if birth_year else None,
            birth_place=birth_place,
            death_year=death_year,
            death_date=str(death_year) if death_year else None,
            death_place=death_place,
            father_name=father_name,
            mother_name=mother_name,
            raw_data={
                "full_name": full_name,
                "collection": collection,
            },
        )

    def _extract_fields(self, card) -> dict[str, str]:
        """Extract labeled field values from a result card."""
        fields: dict[str, str] = {}

        # Try dt/dd pairs
        for dt in card.css("dt, .field-label, span.label"):
            label = dt.text(strip=True).lower().rstrip(":")
            dd = dt.next
            if dd and hasattr(dd, "text"):
                fields[label] = dd.text(strip=True)

        # Try table cells
        for row in card.css("tr"):
            cells = row.css("td, th")
            if len(cells) >= 2:
                label = cells[0].text(strip=True).lower().rstrip(":")
                value = cells[1].text(strip=True)
                if label and value:
                    fields[label] = value

        return fields

    async def get_record_detail(self, record_id: str) -> SourceRecord | None:
        # Full record details require Ancestry subscription
        return None
