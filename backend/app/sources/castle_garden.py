"""Castle Garden adapter.

Pre-Ellis Island (1820-1892) immigration records for the Port of New York.
Complements the Ellis Island adapter for earlier emigration waves.
"""

from __future__ import annotations

import logging
import re

import httpx
from selectolax.parser import HTMLParser

from .base import SourceRecord
from .scraper_base import BaseHTMLScraper

logger = logging.getLogger(__name__)

CG_SEARCH_URL = "https://www.castlegarden.org/searcher.php"


class CastleGardenSource(BaseHTMLScraper):
    name = "castle_garden"
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
            "lnm": surname,
        }
        if given_name:
            params["fnm"] = given_name
        if birth_year:
            # Estimate arrival: age 20-40
            params["yr_from"] = str(birth_year + 15)
            params["yr_to"] = str(birth_year + 45)

        resp = await self.fetch(CG_SEARCH_URL, params)
        if not resp:
            return []

        results = self._parse_results(resp.text)
        logger.info("Castle Garden returned %d results for %s %s", len(results), given_name, surname)
        return results

    def _parse_results(self, html: str) -> list[SourceRecord]:
        tree = HTMLParser(html)
        results = []

        rows = tree.css("table tr, div.result-row, li.passenger")
        for row in rows[:self.max_results]:
            cells = row.css("td")
            if len(cells) < 3:
                link = row.css_first("a[href]")
                if link:
                    record = self._parse_link(link, row)
                    if record:
                        results.append(record)
                continue

            record = self._parse_row(cells, row)
            if record:
                results.append(record)

        return results

    def _parse_row(self, cells, row) -> SourceRecord | None:
        # Typical: Name, Age, Arrival Date, Ship, Occupation, Origin
        full_name = cells[0].text(strip=True)
        if not full_name:
            return None

        parts = full_name.split()
        given = parts[0] if parts else None
        surname = parts[-1] if len(parts) > 1 else None

        row_text = row.text(strip=True)

        # Age
        age = None
        age_match = re.search(r"\b(\d{1,2})\b", cells[1].text(strip=True) if len(cells) > 1 else "")
        if age_match:
            age = int(age_match.group(1))

        # Arrival year
        arrival_year = None
        year_match = re.search(r"\b(1[89]\d{2})\b", row_text)
        if year_match:
            arrival_year = int(year_match.group(1))

        birth_year = None
        if age and arrival_year:
            birth_year = arrival_year - age

        # Origin
        origin = None
        if len(cells) > 4:
            origin = cells[4].text(strip=True) or cells[-1].text(strip=True)

        link = row.css_first("a[href]")
        source_url = None
        if link:
            href = link.attributes.get("href", "")
            if href and not href.startswith("http"):
                href = f"https://www.castlegarden.org/{href}"
            source_url = href

        record_id = f"cg-{full_name.replace(' ', '-')}-{arrival_year or ''}"

        return SourceRecord(
            source_name=self.name,
            source_record_id=record_id,
            source_url=source_url,
            given_name=given,
            surname=surname,
            birth_year=birth_year,
            birth_place=origin,
            event_type="immigration",
            raw_data={
                "arrival_year": arrival_year,
                "age": age,
                "origin": origin,
                "full_text": row_text[:200],
            },
        )

    def _parse_link(self, link, row) -> SourceRecord | None:
        text = link.text(strip=True)
        if not text:
            return None
        parts = text.split()
        given = parts[0] if parts else None
        surname = parts[-1] if len(parts) > 1 else None

        href = link.attributes.get("href", "")
        if not href.startswith("http"):
            href = f"https://www.castlegarden.org/{href}"

        row_text = row.text(strip=True)
        years = re.findall(r"\b(1[89]\d{2})\b", row_text)

        return SourceRecord(
            source_name=self.name,
            source_record_id=f"cg-{text.replace(' ', '-')}",
            source_url=href,
            given_name=given,
            surname=surname,
            event_type="immigration",
            raw_data={"arrival_year": years[0] if years else None},
        )

    async def get_record_detail(self, record_id: str) -> SourceRecord | None:
        return None
