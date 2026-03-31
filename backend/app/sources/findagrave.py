"""Find A Grave scraper adapter.

Searches findagrave.com for memorial records with burial/death information.
No official API - uses the public search interface.
"""

from __future__ import annotations

import asyncio
import logging
import re

import httpx
from selectolax.parser import HTMLParser

from .base import SourceRecord

logger = logging.getLogger(__name__)

FAG_SEARCH_URL = "https://www.findagrave.com/memorial/search"


class FindAGraveSource:
    name = "findagrave"

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

        params: dict[str, str] = {
            "lastname": surname,
        }
        if given_name:
            params["firstname"] = given_name
        if birth_year:
            params["birthyear"] = str(birth_year)
            params["birthyearfilter"] = "5"  # +/- 5 years
        if death_year:
            params["deathyear"] = str(death_year)
            params["deathyearfilter"] = "5"
        if birth_place:
            params["location"] = birth_place

        try:
            resp = await self._client.get(FAG_SEARCH_URL, params=params)
            resp.raise_for_status()
            results = self._parse_results(resp.text)
            logger.info("Find A Grave returned %d results for %s %s", len(results), given_name, surname)
            return results
        except Exception as e:
            logger.error("Find A Grave search failed: %s", e)
            return []

    def _parse_results(self, html: str) -> list[SourceRecord]:
        tree = HTMLParser(html)
        results = []

        # Find memorial entries - they are typically in div.memorial-item or similar containers
        memorials = tree.css("div.memorial-item, div.search-result-item, li.memorial-item")
        if not memorials:
            # Try alternative selectors for different page layouts
            memorials = tree.css("[data-memorial-id]")

        for memorial in memorials:
            try:
                record = self._parse_memorial(memorial)
                if record:
                    results.append(record)
            except Exception as e:
                logger.debug("Failed to parse memorial: %s", e)
                continue

        # Fallback: parse structured data from search results table
        if not results:
            results = self._parse_search_table(tree)

        return results[:50]  # Limit results

    def _parse_memorial(self, node) -> SourceRecord | None:
        # Try to extract memorial ID
        memorial_id = node.attributes.get("data-memorial-id", "")
        if not memorial_id:
            link = node.css_first("a[href*='/memorial/']")
            if link:
                href = link.attributes.get("href", "")
                match = re.search(r"/memorial/(\d+)", href)
                if match:
                    memorial_id = match.group(1)

        if not memorial_id:
            return None

        # Extract name
        name_el = node.css_first("h2, .memorial-name, .name-block a, a.memorial-name")
        full_name = name_el.text(strip=True) if name_el else ""

        # Parse name parts
        given_name = None
        surname = None
        if full_name:
            parts = full_name.split()
            if parts:
                given_name = parts[0]
                surname = parts[-1] if len(parts) > 1 else None

        # Extract dates
        birth_text = ""
        death_text = ""
        dates_el = node.css_first(".memorial-date, .dates, .birth-death-dates")
        if dates_el:
            dates_text = dates_el.text(strip=True)
            # Pattern: "BIRTH_DATE - DEATH_DATE" or "b. DATE - d. DATE"
            date_match = re.search(r"(\d{1,2}\s+\w+\s+\d{4}|\d{4})\s*[-~]\s*(\d{1,2}\s+\w+\s+\d{4}|\d{4})", dates_text)
            if date_match:
                birth_text = date_match.group(1)
                death_text = date_match.group(2)

        # Extract years from date text
        birth_year = None
        death_year = None
        for text, setter in [(birth_text, "birth"), (death_text, "death")]:
            year_match = re.search(r"(\d{4})", text)
            if year_match:
                if setter == "birth":
                    birth_year = int(year_match.group(1))
                else:
                    death_year = int(year_match.group(1))

        # Extract burial location
        location_el = node.css_first(".memorial-location, .cemetery-name, .location")
        burial_place = location_el.text(strip=True) if location_el else None

        source_url = f"https://www.findagrave.com/memorial/{memorial_id}"

        return SourceRecord(
            source_name=self.name,
            source_record_id=f"fag-{memorial_id}",
            source_url=source_url,
            given_name=given_name,
            surname=surname,
            birth_date=birth_text or None,
            birth_year=birth_year,
            death_date=death_text or None,
            death_year=death_year,
            death_place=burial_place,
            raw_data={"memorial_id": memorial_id, "full_name": full_name},
        )

    def _parse_search_table(self, tree: HTMLParser) -> list[SourceRecord]:
        """Fallback parser for table-based search results."""
        results = []
        rows = tree.css("table tr, .search-results-content .result-row")
        for row in rows:
            links = row.css("a[href*='/memorial/']")
            if not links:
                continue
            link = links[0]
            href = link.attributes.get("href", "")
            match = re.search(r"/memorial/(\d+)", href)
            if not match:
                continue

            memorial_id = match.group(1)
            full_name = link.text(strip=True)
            parts = full_name.split()
            given_name = parts[0] if parts else None
            surname = parts[-1] if len(parts) > 1 else None

            # Extract years from row text
            row_text = row.text(strip=True)
            years = re.findall(r"\b(1[5-9]\d{2}|20[0-2]\d)\b", row_text)
            birth_year = int(years[0]) if years else None
            death_year = int(years[1]) if len(years) > 1 else None

            results.append(SourceRecord(
                source_name=self.name,
                source_record_id=f"fag-{memorial_id}",
                source_url=f"https://www.findagrave.com/memorial/{memorial_id}",
                given_name=given_name,
                surname=surname,
                birth_year=birth_year,
                death_year=death_year,
                raw_data={"memorial_id": memorial_id, "full_name": full_name},
            ))

        return results

    async def get_record_detail(self, record_id: str) -> SourceRecord | None:
        """Fetch full memorial detail page."""
        memorial_id = record_id.replace("fag-", "")
        url = f"https://www.findagrave.com/memorial/{memorial_id}"

        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
        except Exception:
            return None

        tree = HTMLParser(resp.text)

        # Extract detailed info from memorial page
        name_el = tree.css_first("h1#bio-name, h1.memorial-name")
        full_name = name_el.text(strip=True) if name_el else ""
        parts = full_name.split()
        given_name = parts[0] if parts else None
        surname = parts[-1] if len(parts) > 1 else None

        # Birth/death info
        birth_el = tree.css_first("#birthDateLabel, .memorial-birth")
        death_el = tree.css_first("#deathDateLabel, .memorial-death")
        birth_text = birth_el.text(strip=True) if birth_el else None
        death_text = death_el.text(strip=True) if death_el else None

        birth_year = None
        death_year = None
        if birth_text:
            m = re.search(r"(\d{4})", birth_text)
            if m:
                birth_year = int(m.group(1))
        if death_text:
            m = re.search(r"(\d{4})", death_text)
            if m:
                death_year = int(m.group(1))

        # Burial location
        cemetery_el = tree.css_first("#cemeteryNameLabel a, .cemetery-name")
        burial_place = cemetery_el.text(strip=True) if cemetery_el else None

        # Family members listed on the memorial
        father_name = None
        mother_name = None
        family_section = tree.css("div.family-member, li.family-member")
        for member in family_section:
            rel_type = member.css_first(".relationship-type, .relation")
            if rel_type:
                rel_text = rel_type.text(strip=True).lower()
                name_link = member.css_first("a")
                if name_link:
                    member_name = name_link.text(strip=True)
                    if "father" in rel_text or "ojciec" in rel_text:
                        father_name = member_name
                    elif "mother" in rel_text or "matka" in rel_text:
                        mother_name = member_name

        return SourceRecord(
            source_name=self.name,
            source_record_id=record_id,
            source_url=url,
            given_name=given_name,
            surname=surname,
            birth_date=birth_text,
            birth_year=birth_year,
            death_date=death_text,
            death_year=death_year,
            death_place=burial_place,
            father_name=father_name,
            mother_name=mother_name,
            raw_data={"memorial_id": memorial_id, "full_name": full_name, "burial": burial_place},
        )
