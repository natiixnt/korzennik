"""BillionGraves scraper adapter.

BillionGraves has GPS-tagged headstone photos with transcribed data.
Searches billiongraves.com for grave records.
"""

from __future__ import annotations

import logging
import re

import httpx
from selectolax.parser import HTMLParser

from .base import SourceRecord

logger = logging.getLogger(__name__)

BG_SEARCH_URL = "https://billiongraves.com/search"
BG_API_URL = "https://billiongraves.com/api/search"


class BillionGravesSource:
    name = "billiongraves"

    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json, text/html",
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

        # Try the JSON API first
        results = await self._search_api(given_name, surname, birth_year, death_year)
        if results:
            return results

        # Fallback to HTML scraping
        return await self._search_html(given_name, surname, birth_year, death_year)

    async def _search_api(
        self, given_name: str | None, surname: str, birth_year: int | None, death_year: int | None
    ) -> list[SourceRecord]:
        """Try the BillionGraves internal API."""
        params = {
            "family_name": surname,
            "page": "1",
            "size": "50",
        }
        if given_name:
            params["given_names"] = given_name
        if birth_year:
            params["birth_year"] = str(birth_year)
            params["birth_year_range"] = "5"
        if death_year:
            params["death_year"] = str(death_year)
            params["death_year_range"] = "5"

        try:
            resp = await self._client.get(BG_API_URL, params=params)
            if resp.status_code != 200:
                return []
            data = resp.json()
        except Exception:
            return []

        results = []
        items = data.get("results", data.get("items", data.get("data", [])))
        if isinstance(items, dict):
            items = items.get("records", items.get("results", []))

        for item in items[:50]:
            record = self._parse_api_item(item)
            if record:
                results.append(record)

        logger.info("BillionGraves API returned %d results for %s %s", len(results), given_name, surname)
        return results

    def _parse_api_item(self, item: dict) -> SourceRecord | None:
        record_id = str(item.get("id", item.get("record_id", "")))
        if not record_id:
            return None

        given = item.get("given_names", item.get("first_name", ""))
        surname = item.get("family_name", item.get("last_name", ""))
        birth_year = item.get("birth_year")
        death_year = item.get("death_year")
        cemetery = item.get("cemetery_name", "")
        location = item.get("cemetery_location", item.get("location", ""))

        if birth_year:
            try:
                birth_year = int(birth_year)
            except (ValueError, TypeError):
                birth_year = None
        if death_year:
            try:
                death_year = int(death_year)
            except (ValueError, TypeError):
                death_year = None

        burial_place = f"{cemetery}, {location}".strip(", ") if cemetery or location else None

        return SourceRecord(
            source_name=self.name,
            source_record_id=f"bg-{record_id}",
            source_url=f"https://billiongraves.com/grave/{record_id}",
            given_name=given or None,
            surname=surname or None,
            birth_year=birth_year,
            birth_date=str(birth_year) if birth_year else None,
            death_year=death_year,
            death_date=str(death_year) if death_year else None,
            death_place=burial_place,
            raw_data=item,
        )

    async def _search_html(
        self, given_name: str | None, surname: str, birth_year: int | None, death_year: int | None
    ) -> list[SourceRecord]:
        """Fallback HTML scraper."""
        params = {"family_name": surname}
        if given_name:
            params["given_names"] = given_name
        if birth_year:
            params["year_range_birth"] = f"{birth_year - 5}-{birth_year + 5}"
        if death_year:
            params["year_range_death"] = f"{death_year - 5}-{death_year + 5}"

        try:
            resp = await self._client.get(BG_SEARCH_URL, params=params)
            resp.raise_for_status()
        except Exception as e:
            logger.error("BillionGraves HTML search failed: %s", e)
            return []

        tree = HTMLParser(resp.text)
        results = []

        cards = tree.css("div.record-card, div.grave-card, a.record-link, tr.record-row")
        for card in cards[:50]:
            link = card.css_first("a[href*='/grave/']")
            if not link:
                if card.tag == "a":
                    link = card
                else:
                    continue

            href = link.attributes.get("href", "")
            match = re.search(r"/grave/(\d+)", href)
            if not match:
                continue

            record_id = match.group(1)
            text = card.text(strip=True)

            # Extract name
            name_parts = text.split()
            given = name_parts[0] if name_parts else None
            sur = name_parts[-1] if len(name_parts) > 1 else None

            # Extract years
            years = re.findall(r"\b(1[5-9]\d{2}|20[0-2]\d)\b", text)
            b_year = int(years[0]) if years else None
            d_year = int(years[1]) if len(years) > 1 else None

            results.append(SourceRecord(
                source_name=self.name,
                source_record_id=f"bg-{record_id}",
                source_url=f"https://billiongraves.com/grave/{record_id}",
                given_name=given,
                surname=sur,
                birth_year=b_year,
                death_year=d_year,
                raw_data={"record_id": record_id},
            ))

        logger.info("BillionGraves HTML returned %d results for %s %s", len(results), given_name, surname)
        return results

    async def get_record_detail(self, record_id: str) -> SourceRecord | None:
        bg_id = record_id.replace("bg-", "")
        url = f"https://billiongraves.com/grave/{bg_id}"

        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
        except Exception:
            return None

        tree = HTMLParser(resp.text)

        name_el = tree.css_first("h1.grave-name, h1")
        full_name = name_el.text(strip=True) if name_el else ""
        parts = full_name.split()
        given = parts[0] if parts else None
        sur = parts[-1] if len(parts) > 1 else None

        text = tree.body.text(strip=True) if tree.body else ""
        years = re.findall(r"\b(1[5-9]\d{2}|20[0-2]\d)\b", text)

        cemetery_el = tree.css_first(".cemetery-name, a[href*='/cemetery/']")
        burial = cemetery_el.text(strip=True) if cemetery_el else None

        return SourceRecord(
            source_name=self.name,
            source_record_id=record_id,
            source_url=url,
            given_name=given,
            surname=sur,
            birth_year=int(years[0]) if years else None,
            death_year=int(years[1]) if len(years) > 1 else None,
            death_place=burial,
            raw_data={"full_name": full_name},
        )
