"""Geneteka scraper adapter.

Geneteka (geneteka.genealodzy.pl) is a Polish genealogical index database
with no official API. We scrape the HTML search results.
"""

from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import urlencode

import httpx
from selectolax.parser import HTMLParser

from ..config import settings
from .base import SourceRecord

logger = logging.getLogger(__name__)

GENETEKA_BASE = "https://geneteka.genealodzy.pl/index.php"

# Polish voivodeship -> Geneteka region codes
REGION_CODES = {
    "dolnoslaskie": "02ds",
    "kujawsko-pomorskie": "04kp",
    "lubelskie": "06lb",
    "lubuskie": "08lu",
    "lodzkie": "10ld",
    "malopolskie": "12mp",
    "mazowieckie": "14mz",
    "opolskie": "16op",
    "podkarpackie": "18pk",
    "podlaskie": "20pd",
    "pomorskie": "22pm",
    "slaskie": "24sl",
    "swietokrzyskie": "26sk",
    "warminsko-mazurskie": "28wm",
    "wielkopolskie": "30wp",
    "zachodniopomorskie": "32zp",
    # Special: all regions
    "all": "00all",
}


class GenetekaSource:
    name = "geneteka"

    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Korzennik/0.1 (genealogy research tool)",
            },
        )
        self._delay = settings.geneteka_delay_seconds

    def _guess_region(self, place: str | None) -> str:
        """Try to match a place name to a Geneteka region code."""
        if not place:
            return "00all"
        place_lower = place.lower()
        for region, code in REGION_CODES.items():
            if region in place_lower:
                return code
        # Common city -> region mappings
        city_map = {
            "warszawa": "14mz", "krakow": "12mp", "krakaw": "12mp",
            "lodz": "10ld", "wroclaw": "02ds", "poznan": "30wp",
            "gdansk": "22pm", "lublin": "06lb", "katowice": "24sl",
            "bialystok": "20pd", "rzeszow": "18pk", "kielce": "26sk",
            "olsztyn": "28wm", "opole": "16op", "szczecin": "32zp",
            "bydgoszcz": "04kp", "torun": "04kp", "zielona gora": "08lu",
            "gorzow": "08lu", "radom": "14mz", "plock": "14mz",
        }
        for city, code in city_map.items():
            if city in place_lower:
                return code
        return "00all"

    def _parse_results(self, html: str, record_type: str) -> list[SourceRecord]:
        """Parse Geneteka HTML results table into SourceRecords."""
        tree = HTMLParser(html)
        results = []

        # Find result tables
        tables = tree.css("table.table-bordered")
        for table in tables:
            rows = table.css("tr")
            for row in rows[1:]:  # Skip header
                cells = row.css("td")
                if len(cells) < 5:
                    continue

                # Typical columns: Year, Parish, Name, Surname, Parents, Notes/Link
                year_text = cells[0].text(strip=True)
                parish = cells[1].text(strip=True) if len(cells) > 1 else ""
                name = cells[2].text(strip=True) if len(cells) > 2 else ""
                surname = cells[3].text(strip=True) if len(cells) > 3 else ""
                parents_text = cells[4].text(strip=True) if len(cells) > 4 else ""

                # Parse year
                year = None
                year_match = re.search(r"(\d{4})", year_text)
                if year_match:
                    year = int(year_match.group(1))

                # Parse parents (format: "father_name / mother_maiden_name")
                father_name = None
                mother_name = None
                if "/" in parents_text:
                    parts = parents_text.split("/")
                    father_name = parts[0].strip() or None
                    mother_name = parts[1].strip() if len(parts) > 1 else None

                # Build a unique record ID
                record_id = f"geneteka-{record_type}-{year}-{parish}-{surname}-{name}"

                # Try to get link to full record
                link = None
                link_tag = row.css_first("a[href]")
                if link_tag:
                    href = link_tag.attributes.get("href", "")
                    if href and not href.startswith("#"):
                        if not href.startswith("http"):
                            href = f"https://geneteka.genealodzy.pl/{href}"
                        link = href

                record = SourceRecord(
                    source_name=self.name,
                    source_record_id=record_id,
                    source_url=link,
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

                # Assign dates based on record type
                if record_type == "birth":
                    record.birth_year = year
                    record.birth_date = year_text
                    record.birth_place = parish
                elif record_type == "death":
                    record.death_year = year
                    record.death_date = year_text
                    record.death_place = parish
                elif record_type == "marriage":
                    record.raw_data["marriage_year"] = year
                    record.raw_data["marriage_place"] = parish

                results.append(record)

        return results

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

        region = self._guess_region(birth_place)
        all_results: list[SourceRecord] = []

        # Search births, deaths, marriages
        record_types = {"B": "birth", "D": "death", "S": "marriage"}
        for bdm_code, record_type in record_types.items():
            params = {
                "op": "gt",
                "lang": "eng",
                "bdm": bdm_code,
                "w": region,
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

            url = f"{GENETEKA_BASE}?{urlencode(params)}"

            try:
                resp = await self._client.get(url)
                resp.raise_for_status()
                results = self._parse_results(resp.text, record_type)
                all_results.extend(results)
            except Exception as e:
                logger.error("Geneteka search failed for %s %s: %s", bdm_code, surname, e)

            # Be respectful with rate limiting
            await asyncio.sleep(self._delay)

        logger.info(
            "Geneteka returned %d results for %s %s",
            len(all_results), given_name, surname,
        )
        return all_results

    async def get_record_detail(self, record_id: str) -> SourceRecord | None:
        # Geneteka doesn't have individual record detail pages in a structured way
        return None
