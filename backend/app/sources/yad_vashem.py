"""Yad Vashem Central Database of Shoah Victims adapter.

4.8+ million names of Holocaust victims with pre-war residence,
family relationships, and biographical details.
"""

from __future__ import annotations

import logging
import re

import httpx
from selectolax.parser import HTMLParser

from .base import SourceRecord
from .scraper_base import BaseHTMLScraper

logger = logging.getLogger(__name__)

YV_SEARCH_URL = "https://yvng.yadvashem.org/index.html"
YV_API_URL = "https://yvng.yadvashem.org/nameSearch.html"


class YadVashemSource(BaseHTMLScraper):
    name = "yad_vashem"
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
            "language": "en",
            "action": "searchPerson",
            "Last+Name": surname,
        }
        if given_name:
            params["First+Name"] = given_name
        if birth_place:
            params["Place+of+Residence"] = birth_place

        resp = await self.fetch(YV_API_URL, params)
        if not resp:
            return []

        results = self._parse_results(resp.text)
        logger.info("Yad Vashem returned %d results for %s %s", len(results), given_name, surname)
        return results

    def _parse_results(self, html: str) -> list[SourceRecord]:
        tree = HTMLParser(html)
        results = []

        rows = tree.css("tr.result, div.result-item, li.victim-item, table tbody tr")
        for row in rows[:self.max_results]:
            cells = row.css("td")
            if len(cells) < 3:
                # Try link-based parsing
                link = row.css_first("a[href]")
                if link:
                    record = self._parse_link_result(link, row)
                    if record:
                        results.append(record)
                continue

            record = self._parse_row(cells, row)
            if record:
                results.append(record)

        return results

    def _parse_row(self, cells, row) -> SourceRecord | None:
        surname = cells[0].text(strip=True) if cells else ""
        given = cells[1].text(strip=True) if len(cells) > 1 else ""

        if not surname:
            return None

        # Additional fields vary
        row_text = row.text(strip=True)

        birth_year = None
        birth_place = None
        father_name = None
        mother_name = None

        # Extract birth year
        year_match = re.search(r"(?:born|b\.|ur\.?)\s*(\d{4})", row_text, re.IGNORECASE)
        if year_match:
            birth_year = int(year_match.group(1))
        else:
            years = re.findall(r"\b(1[89]\d{2}|19[0-4]\d)\b", row_text)
            if years:
                birth_year = int(years[0])

        # Residence/place
        place_match = re.search(
            r"(?:residence|lived in|from|mieszka)\s*:?\s*([\w\s,]+?)(?:\s*[-;.]|$)",
            row_text, re.IGNORECASE,
        )
        if place_match:
            birth_place = place_match.group(1).strip()

        # Family
        father_match = re.search(r"(?:father|ojciec)\s*:?\s*(\w+)", row_text, re.IGNORECASE)
        if father_match:
            father_name = father_match.group(1)
        mother_match = re.search(r"(?:mother|matka)\s*:?\s*(\w+)", row_text, re.IGNORECASE)
        if mother_match:
            mother_name = mother_match.group(1)

        link = row.css_first("a[href]")
        source_url = None
        record_id = f"yv-{surname}-{given}-{birth_year or ''}"
        if link:
            href = link.attributes.get("href", "")
            if href:
                if not href.startswith("http"):
                    href = f"https://yvng.yadvashem.org/{href}"
                source_url = href
                id_match = re.search(r"id=(\d+)", href)
                if id_match:
                    record_id = f"yv-{id_match.group(1)}"

        return SourceRecord(
            source_name=self.name,
            source_record_id=record_id,
            source_url=source_url,
            given_name=given or None,
            surname=surname or None,
            birth_year=birth_year,
            birth_date=str(birth_year) if birth_year else None,
            birth_place=birth_place,
            father_name=father_name,
            mother_name=mother_name,
            event_type="death",
            raw_data={"source": "Yad Vashem", "row_text": row_text[:300]},
        )

    def _parse_link_result(self, link, row) -> SourceRecord | None:
        href = link.attributes.get("href", "")
        text = link.text(strip=True)
        if not text:
            return None

        parts = text.split()
        given = parts[0] if parts else None
        surname = parts[-1] if len(parts) > 1 else None

        if not href.startswith("http"):
            href = f"https://yvng.yadvashem.org/{href}"

        row_text = row.text(strip=True)
        years = re.findall(r"\b(1[89]\d{2}|19[0-4]\d)\b", row_text)

        return SourceRecord(
            source_name=self.name,
            source_record_id=f"yv-{text.replace(' ', '-')}",
            source_url=href,
            given_name=given,
            surname=surname,
            birth_year=int(years[0]) if years else None,
            event_type="death",
            raw_data={"source": "Yad Vashem"},
        )

    async def get_record_detail(self, record_id: str) -> SourceRecord | None:
        return None
