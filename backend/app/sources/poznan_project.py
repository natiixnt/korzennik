"""Poznan Project adapter (poznan-project.psnc.pl).

Marriage index from Wielkopolska/Greater Poland region.
Extremely valuable: marriage records name parents of both bride and groom,
giving 4 parent names per record.
"""

from __future__ import annotations

import asyncio
import logging
import re

import httpx
from selectolax.parser import HTMLParser

from .base import SourceRecord
from .scraper_base import BaseHTMLScraper

logger = logging.getLogger(__name__)

POZNAN_SEARCH_URL = "https://poznan-project.psnc.pl/search"


class PoznanProjectSource(BaseHTMLScraper):
    name = "poznan_project"
    delay_seconds = 2.0

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

        params = {
            "lastname": surname,
        }
        if given_name:
            params["firstname"] = given_name
        # Marriage records: estimate marriage year from birth year (+20-35)
        if birth_year:
            params["year_from"] = str(birth_year + 18)
            params["year_to"] = str(birth_year + 40)

        resp = await self.fetch(POZNAN_SEARCH_URL, params)
        if not resp:
            return []

        results = self._parse_results(resp.text)
        logger.info("Poznan Project returned %d results for %s %s", len(results), given_name, surname)
        return results

    def _parse_results(self, html: str) -> list[SourceRecord]:
        tree = HTMLParser(html)
        results = []

        # Poznan Project results are typically in a table
        rows = tree.css("table tr, div.result-row, li.result")
        for row in rows[:self.max_results]:
            cells = row.css("td")
            if len(cells) < 4:
                continue

            try:
                record = self._parse_marriage_row(cells, row)
                if record:
                    results.append(record)
            except Exception as e:
                logger.debug("Failed to parse Poznan row: %s", e)

        return results

    def _parse_marriage_row(self, cells, row) -> SourceRecord | None:
        # Typical Poznan Project columns:
        # Year | Parish | Groom (name, father) | Bride (name, father) | Notes
        row_text = row.text(strip=True)

        # Extract year
        year = None
        year_match = re.search(r"\b(1[6-9]\d{2}|20[0-2]\d)\b", cells[0].text(strip=True))
        if year_match:
            year = int(year_match.group(1))

        # Parish
        parish = cells[1].text(strip=True) if len(cells) > 1 else ""

        # Groom info (typically: "Given SURNAME s. Father_Given [FATHER_SURNAME]")
        groom_text = cells[2].text(strip=True) if len(cells) > 2 else ""
        groom_given, groom_surname, groom_father = self._parse_person_with_parent(groom_text)

        # Bride info (similar format)
        bride_text = cells[3].text(strip=True) if len(cells) > 3 else ""
        bride_given, bride_surname, bride_father = self._parse_person_with_parent(bride_text)

        # Try to extract mother names from additional columns or notes
        notes = cells[4].text(strip=True) if len(cells) > 4 else ""

        # Build record ID
        record_id = f"pp-{year}-{parish}-{groom_surname}-{bride_surname}"

        # Get link if available
        link = row.css_first("a[href]")
        source_url = None
        if link:
            href = link.attributes.get("href", "")
            if href and not href.startswith("http"):
                href = f"https://poznan-project.psnc.pl{href}"
            source_url = href

        # Create two records: one for groom, one for bride (both contain parent info)
        # Return the groom record (primary); the bride record can be extracted later
        return SourceRecord(
            source_name=self.name,
            source_record_id=record_id,
            source_url=source_url,
            given_name=groom_given,
            surname=groom_surname,
            event_type="marriage",
            father_name=groom_father,
            raw_data={
                "year": year,
                "parish": parish,
                "groom": groom_text,
                "bride": bride_text,
                "bride_given": bride_given,
                "bride_surname": bride_surname,
                "bride_father": bride_father,
                "notes": notes,
                "record_type": "marriage",
            },
        )

    def _parse_person_with_parent(self, text: str) -> tuple[str | None, str | None, str | None]:
        """Parse a person entry like 'Jan KOWALSKI s. Wojciech' or 'Maria NOWAK d. Franciszek'.

        Returns (given_name, surname, parent_given_name).
        """
        if not text:
            return None, None, None

        # Pattern: "Given SURNAME s./d. ParentGiven [PARENTSURNAME]"
        parent_match = re.search(r"\b[sd]\.\s*(\w+)", text, re.IGNORECASE)
        parent_given = parent_match.group(1) if parent_match else None

        # Remove the parent part for name parsing
        name_part = re.sub(r"\b[sd]\.\s*.*$", "", text, flags=re.IGNORECASE).strip()

        parts = name_part.split()
        given = parts[0] if parts else None
        surname = None
        # Surnames are often in UPPERCASE
        for part in parts[1:]:
            if part.isupper() or (len(parts) > 1 and part == parts[-1]):
                surname = part.title()
                break

        if not surname and len(parts) > 1:
            surname = parts[-1]

        return given, surname, parent_given

    async def get_record_detail(self, record_id: str) -> SourceRecord | None:
        return None
