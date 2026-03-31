"""JRI-Poland (Jewish Records Indexing - Poland) adapter.

Largest index of Jewish vital records from Poland: births, marriages,
deaths from thousands of towns. Critical for Jewish genealogy research.
"""

from __future__ import annotations

import logging
import re

import httpx
from selectolax.parser import HTMLParser

from .base import SourceRecord
from .scraper_base import BaseHTMLScraper

logger = logging.getLogger(__name__)

JRI_SEARCH_URL = "https://jri-poland.org/jriplweb.htm"
JRI_RESULTS_URL = "https://jri-poland.org/search.php"


class JRIPolandSource(BaseHTMLScraper):
    name = "jri_poland"
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
            "surname": surname,
            "search": "Search",
        }
        if given_name:
            params["given"] = given_name
        if birth_place:
            params["town"] = birth_place

        resp = await self.fetch(JRI_RESULTS_URL, params)
        if not resp:
            return []

        results = self._parse_results(resp.text)
        logger.info("JRI-Poland returned %d results for %s %s", len(results), given_name, surname)
        return results

    def _parse_results(self, html: str) -> list[SourceRecord]:
        tree = HTMLParser(html)
        results = []

        # JRI-Poland results in tables
        rows = tree.css("table tr, div.result-row")
        for row in rows[:self.max_results]:
            cells = row.css("td")
            if len(cells) < 4:
                continue

            try:
                record = self._parse_row(cells, row)
                if record:
                    results.append(record)
            except Exception as e:
                logger.debug("Failed to parse JRI row: %s", e)

        return results

    def _parse_row(self, cells, row) -> SourceRecord | None:
        # Typical JRI columns: Surname, Given Name, Town, Year, Record Type, Father, Mother
        row_text = row.text(strip=True)

        surname = cells[0].text(strip=True) if cells else ""
        given = cells[1].text(strip=True) if len(cells) > 1 else ""
        town = cells[2].text(strip=True) if len(cells) > 2 else ""
        year_text = cells[3].text(strip=True) if len(cells) > 3 else ""
        record_type_text = cells[4].text(strip=True).lower() if len(cells) > 4 else ""
        father = cells[5].text(strip=True) if len(cells) > 5 else ""
        mother = cells[6].text(strip=True) if len(cells) > 6 else ""

        if not surname:
            return None

        year = None
        year_match = re.search(r"(\d{4})", year_text)
        if year_match:
            year = int(year_match.group(1))

        # Map record type
        event_type = "birth"
        if "death" in record_type_text or "zgon" in record_type_text:
            event_type = "death"
        elif "marriage" in record_type_text or "slub" in record_type_text:
            event_type = "marriage"

        record_id = f"jri-{year}-{town}-{surname}-{given}"

        link = row.css_first("a[href]")
        source_url = None
        if link:
            href = link.attributes.get("href", "")
            if href and not href.startswith("http"):
                href = f"https://jri-poland.org/{href}"
            source_url = href

        record = SourceRecord(
            source_name=self.name,
            source_record_id=record_id,
            source_url=source_url,
            given_name=given or None,
            surname=surname or None,
            event_type=event_type,
            father_name=father or None,
            mother_name=mother or None,
            raw_data={
                "town": town,
                "year": year_text,
                "record_type": record_type_text,
            },
        )

        if event_type == "birth":
            record.birth_year = year
            record.birth_date = year_text
            record.birth_place = town
        elif event_type == "death":
            record.death_year = year
            record.death_date = year_text
            record.death_place = town

        return record

    async def get_record_detail(self, record_id: str) -> SourceRecord | None:
        return None
