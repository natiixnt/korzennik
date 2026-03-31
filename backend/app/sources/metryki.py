"""Metryki.genealodzy.pl adapter.

Polish Genealogical Society's index of parish and civil records.
Massive coverage of pre-1900 vital records across Poland.
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

METRYKI_BASE = "https://metryki.genealodzy.pl"
METRYKI_SEARCH = f"{METRYKI_BASE}/metryki.php"


class MetrykiSource(BaseHTMLScraper):
    name = "metryki"
    delay_seconds = 1.5

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

        all_results: list[SourceRecord] = []

        # Search births, deaths, marriages
        for record_type, bdm in [("birth", "B"), ("death", "D"), ("marriage", "S")]:
            params = {
                "op": "se",
                "lang": "pol",
                "bdm": bdm,
                "w": "",
                "search_lastname": surname,
            }
            if given_name:
                params["search_name"] = given_name
            if birth_year and record_type == "birth":
                params["from_date"] = str(birth_year - 5)
                params["to_date"] = str(birth_year + 5)
            elif death_year and record_type == "death":
                params["from_date"] = str(death_year - 5)
                params["to_date"] = str(death_year + 5)

            resp = await self.fetch(METRYKI_SEARCH, params)
            if resp:
                results = self._parse_results(resp.text, record_type)
                all_results.extend(results)

        logger.info("Metryki returned %d results for %s %s", len(all_results), given_name, surname)
        return all_results

    def _parse_results(self, html: str, record_type: str) -> list[SourceRecord]:
        tree = HTMLParser(html)
        results = []

        tables = tree.css("table")
        for table in tables:
            rows = table.css("tr")
            for row in rows[1:]:  # Skip header
                cells = row.css("td")
                if len(cells) < 4:
                    continue

                year_text = cells[0].text(strip=True)
                parish = cells[1].text(strip=True) if len(cells) > 1 else ""
                name = cells[2].text(strip=True) if len(cells) > 2 else ""
                surname = cells[3].text(strip=True) if len(cells) > 3 else ""
                parents_text = cells[4].text(strip=True) if len(cells) > 4 else ""

                year = None
                year_match = re.search(r"(\d{4})", year_text)
                if year_match:
                    year = int(year_match.group(1))

                father_name = None
                mother_name = None
                if "/" in parents_text:
                    parts = parents_text.split("/")
                    father_name = parts[0].strip() or None
                    mother_name = parts[1].strip() if len(parts) > 1 else None

                record_id = f"metryki-{record_type}-{year}-{parish}-{surname}-{name}"

                link = row.css_first("a[href]")
                source_url = None
                if link:
                    href = link.attributes.get("href", "")
                    if href and not href.startswith("http"):
                        href = f"{METRYKI_BASE}/{href}"
                    source_url = href

                record = SourceRecord(
                    source_name=self.name,
                    source_record_id=record_id,
                    source_url=source_url,
                    given_name=name or None,
                    surname=surname or None,
                    event_type=record_type,
                    father_name=father_name,
                    mother_name=mother_name,
                    raw_data={
                        "year": year_text,
                        "parish": parish,
                        "parents": parents_text,
                        "record_type": record_type,
                    },
                )

                if record_type == "birth":
                    record.birth_year = year
                    record.birth_date = year_text
                    record.birth_place = parish
                elif record_type == "death":
                    record.death_year = year
                    record.death_date = year_text
                    record.death_place = parish

                results.append(record)

                if len(results) >= self.max_results:
                    return results

        return results

    async def get_record_detail(self, record_id: str) -> SourceRecord | None:
        return None
