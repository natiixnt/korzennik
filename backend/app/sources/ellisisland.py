"""Ellis Island / Statue of Liberty passenger manifest adapter.

Searches the Statue of Liberty - Ellis Island Foundation passenger database
(heritage.statueofliberty.org) for immigration records of passengers who
arrived at Ellis Island and the Port of New York.
"""

from __future__ import annotations

import logging
import re

import httpx
from selectolax.parser import HTMLParser

from .base import SourceRecord

logger = logging.getLogger(__name__)

# The heritage site uses a search form that returns results via POST
HERITAGE_BASE = "https://heritage.statueofliberty.org"
HERITAGE_SEARCH = f"{HERITAGE_BASE}/passenger"


class EllisIslandSource:
    name = "ellisisland"

    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/json",
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

        # Try the search API
        params: dict[str, str] = {
            "lastName": surname,
        }
        if given_name:
            params["firstName"] = given_name
        if birth_year:
            params["birthYear"] = str(birth_year)
            params["birthYearRange"] = "5"
        if birth_place:
            # Map common Polish place names to country for the filter
            params["ethnicity"] = self._guess_ethnicity(birth_place)

        try:
            resp = await self._client.get(HERITAGE_SEARCH, params=params)
            resp.raise_for_status()

            # Try JSON first (some endpoints return JSON)
            if "application/json" in resp.headers.get("content-type", ""):
                return self._parse_json_results(resp.json())

            # Otherwise parse HTML
            return self._parse_html_results(resp.text)
        except Exception as e:
            logger.error("Ellis Island search failed: %s", e)
            return []

    def _guess_ethnicity(self, place: str) -> str:
        """Map birth place to ethnicity/nationality filter."""
        place_lower = place.lower()
        mappings = {
            "poland": "Polish", "polska": "Polish", "polen": "Polish",
            "galicja": "Polish", "galicia": "Polish",
            "russia": "Russian", "rosja": "Russian",
            "germany": "German", "niemcy": "German", "prussia": "German",
            "austria": "Austrian", "austro": "Austrian",
            "ukraine": "Ukrainian", "ukraina": "Ukrainian",
            "lithuania": "Lithuanian", "litwa": "Lithuanian",
        }
        for key, ethnicity in mappings.items():
            if key in place_lower:
                return ethnicity
        return "Polish"  # Default for this tool's primary use case

    def _parse_json_results(self, data: dict | list) -> list[SourceRecord]:
        results = []
        items = data if isinstance(data, list) else data.get("results", data.get("passengers", []))

        for item in items[:50]:
            record = self._parse_json_passenger(item)
            if record:
                results.append(record)

        return results

    def _parse_json_passenger(self, item: dict) -> SourceRecord | None:
        record_id = str(item.get("id", item.get("passengerId", "")))
        if not record_id:
            return None

        given = item.get("firstName", item.get("givenName", ""))
        surname = item.get("lastName", item.get("surname", ""))
        age = item.get("age")
        arrival_year = item.get("arrivalYear", item.get("year"))
        departure_port = item.get("departurePort", item.get("portOfDeparture", ""))
        arrival_date = item.get("arrivalDate", "")
        ship_name = item.get("shipName", item.get("vesselName", ""))
        ethnicity = item.get("ethnicity", item.get("nationality", ""))
        residence = item.get("placeOfResidence", item.get("lastResidence", ""))

        # Estimate birth year from age and arrival year
        birth_year = None
        if age and arrival_year:
            try:
                birth_year = int(arrival_year) - int(age)
            except (ValueError, TypeError):
                pass

        source_url = f"{HERITAGE_BASE}/passenger/{record_id}"

        return SourceRecord(
            source_name=self.name,
            source_record_id=f"ellis-{record_id}",
            source_url=source_url,
            given_name=given or None,
            surname=surname or None,
            birth_year=birth_year,
            birth_place=residence or ethnicity or None,
            raw_data={
                "ship_name": ship_name,
                "arrival_date": arrival_date,
                "departure_port": departure_port,
                "age": age,
                "ethnicity": ethnicity,
                "residence": residence,
                "arrival_year": arrival_year,
            },
        )

    def _parse_html_results(self, html: str) -> list[SourceRecord]:
        tree = HTMLParser(html)
        results = []

        # Parse result rows - the heritage site uses tables or card layouts
        rows = tree.css(
            "tr.passenger-row, div.passenger-result, "
            "div.result-item, table.results tbody tr"
        )

        for row in rows[:50]:
            record = self._parse_html_row(row)
            if record:
                results.append(record)

        # Fallback: try links with passenger IDs
        if not results:
            links = tree.css("a[href*='/passenger/']")
            seen = set()
            for link in links[:50]:
                href = link.attributes.get("href", "")
                match = re.search(r"/passenger/(\d+)", href)
                if not match or match.group(1) in seen:
                    continue
                seen.add(match.group(1))

                text = link.text(strip=True)
                parts = text.split()
                given = parts[0] if parts else None
                sur = parts[-1] if len(parts) > 1 else None

                # Find year in surrounding text
                parent = link.parent
                parent_text = parent.text(strip=True) if parent else text
                years = re.findall(r"\b(1[89]\d{2}|19[0-5]\d)\b", parent_text)

                results.append(SourceRecord(
                    source_name=self.name,
                    source_record_id=f"ellis-{match.group(1)}",
                    source_url=f"{HERITAGE_BASE}/passenger/{match.group(1)}",
                    given_name=given,
                    surname=sur,
                    raw_data={"arrival_year": years[0] if years else None},
                ))

        logger.info("Ellis Island returned %d results", len(results))
        return results

    def _parse_html_row(self, row) -> SourceRecord | None:
        cells = row.css("td")
        if len(cells) < 3:
            return None

        # Typical columns: Name, Age, Arrival Date, Ship, Port of Departure, etc.
        link = row.css_first("a[href*='/passenger/']")
        if not link:
            return None

        href = link.attributes.get("href", "")
        match = re.search(r"/passenger/(\d+)", href)
        if not match:
            return None

        record_id = match.group(1)
        full_name = link.text(strip=True)
        parts = full_name.split()
        given = parts[0] if parts else None
        surname = parts[-1] if len(parts) > 1 else None

        row_text = row.text(strip=True)

        # Extract age
        age = None
        age_match = re.search(r"\b(\d{1,2})\b", cells[1].text(strip=True) if len(cells) > 1 else "")
        if age_match:
            age = int(age_match.group(1))

        # Extract arrival year
        arrival_year = None
        year_match = re.search(r"\b(1[89]\d{2}|19[0-5]\d)\b", row_text)
        if year_match:
            arrival_year = int(year_match.group(1))

        birth_year = None
        if age and arrival_year:
            birth_year = arrival_year - age

        return SourceRecord(
            source_name=self.name,
            source_record_id=f"ellis-{record_id}",
            source_url=f"{HERITAGE_BASE}/passenger/{record_id}",
            given_name=given,
            surname=surname,
            birth_year=birth_year,
            raw_data={
                "arrival_year": arrival_year,
                "age": age,
                "full_text": row_text[:200],
            },
        )

    async def get_record_detail(self, record_id: str) -> SourceRecord | None:
        pid = record_id.replace("ellis-", "")
        url = f"{HERITAGE_BASE}/passenger/{pid}"

        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
        except Exception:
            return None

        tree = HTMLParser(resp.text)
        full_text = tree.body.text(strip=True) if tree.body else ""

        # Extract structured fields from detail page
        fields: dict[str, str] = {}
        for label_el in tree.css("dt, th, .field-label, label"):
            label = label_el.text(strip=True).lower().rstrip(":")
            value_el = label_el.next
            if value_el:
                fields[label] = value_el.text(strip=True) if hasattr(value_el, "text") else str(value_el)

        given = fields.get("first name", fields.get("given name"))
        surname = fields.get("last name", fields.get("surname"))
        age = fields.get("age")
        ship = fields.get("ship", fields.get("vessel"))
        arrival = fields.get("arrival date", fields.get("date of arrival"))
        departure_port = fields.get("port of departure")
        residence = fields.get("place of residence", fields.get("last residence"))
        ethnicity = fields.get("ethnicity", fields.get("nationality"))

        birth_year = None
        if age and arrival:
            year_match = re.search(r"(\d{4})", arrival)
            if year_match:
                try:
                    birth_year = int(year_match.group(1)) - int(age)
                except (ValueError, TypeError):
                    pass

        return SourceRecord(
            source_name=self.name,
            source_record_id=record_id,
            source_url=url,
            given_name=given,
            surname=surname,
            birth_year=birth_year,
            birth_place=residence or ethnicity,
            raw_data={
                "ship": ship,
                "arrival": arrival,
                "departure_port": departure_port,
                "ethnicity": ethnicity,
                "residence": residence,
                "full_text": full_text[:500],
            },
        )
