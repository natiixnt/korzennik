"""WikiTree API adapter.

WikiTree has a public API at api.wikitree.com - no authentication
required for public profiles. Returns structured family data.
"""

from __future__ import annotations

import logging

import httpx

from .base import SourceRecord

logger = logging.getLogger(__name__)

WIKITREE_API = "https://api.wikitree.com/api.php"


class WikiTreeSource:
    name = "wikitree"

    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
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

        # WikiTree uses POST with form data
        data = {
            "action": "searchPerson",
            "LastName": surname,
            "limit": "50",
            "start": "0",
            "fields": "Id,Name,FirstName,LastNameAtBirth,LastNameCurrent,"
                      "BirthDate,BirthDateDecade,BirthLocation,"
                      "DeathDate,DeathDateDecade,DeathLocation,"
                      "Father,Mother,Gender",
        }
        if given_name:
            data["FirstName"] = given_name
        if birth_year:
            data["birthDate"] = str(birth_year)
        if birth_place:
            data["birthLocation"] = birth_place

        try:
            resp = await self._client.post(WIKITREE_API, data=data)
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            logger.error("WikiTree search failed: %s", e)
            return []

        # Parse response
        results = []
        # Response format varies: list of dicts under various keys
        persons = result if isinstance(result, list) else result.get("searchResult", result.get("people", []))
        if isinstance(persons, dict):
            persons = list(persons.values())

        for person in persons[:50]:
            if not isinstance(person, dict):
                continue
            record = self._parse_person(person)
            if record:
                results.append(record)

        logger.info("WikiTree returned %d results for %s %s", len(results), given_name, surname)
        return results

    def _parse_person(self, person: dict) -> SourceRecord | None:
        wt_id = person.get("Name") or person.get("Id")
        if not wt_id:
            return None

        given = person.get("FirstName", "")
        surname = person.get("LastNameAtBirth") or person.get("LastNameCurrent", "")
        birth_date = person.get("BirthDate", "")
        birth_location = person.get("BirthLocation", "")
        death_date = person.get("DeathDate", "")
        death_location = person.get("DeathLocation", "")

        # Parse years
        birth_year = self._parse_year(birth_date) or self._parse_decade(person.get("BirthDateDecade"))
        death_year = self._parse_year(death_date) or self._parse_decade(person.get("DeathDateDecade"))

        # Father/Mother from IDs
        father_id = person.get("Father")
        mother_id = person.get("Mother")

        return SourceRecord(
            source_name=self.name,
            source_record_id=f"wt-{wt_id}",
            source_url=f"https://www.wikitree.com/wiki/{wt_id}",
            given_name=given or None,
            surname=surname or None,
            birth_date=birth_date or None,
            birth_year=birth_year,
            birth_place=birth_location or None,
            death_date=death_date or None,
            death_year=death_year,
            death_place=death_location or None,
            event_type="tree",
            raw_data={
                "wikitree_id": wt_id,
                "father_id": father_id,
                "mother_id": mother_id,
                "gender": person.get("Gender"),
            },
        )

    def _parse_year(self, date_str: str | None) -> int | None:
        if not date_str:
            return None
        parts = date_str.split("-")
        if parts and parts[0].isdigit() and len(parts[0]) == 4:
            year = int(parts[0])
            if 1400 <= year <= 2030:
                return year
        return None

    def _parse_decade(self, decade: str | None) -> int | None:
        if not decade:
            return None
        # Format: "1880s"
        decade = decade.rstrip("s")
        if decade.isdigit() and len(decade) == 4:
            return int(decade) + 5  # Midpoint of decade
        return None

    async def get_record_detail(self, record_id: str) -> SourceRecord | None:
        wt_id = record_id.replace("wt-", "")
        data = {
            "action": "getProfile",
            "key": wt_id,
            "fields": "Id,Name,FirstName,MiddleName,LastNameAtBirth,LastNameCurrent,"
                      "BirthDate,BirthLocation,DeathDate,DeathLocation,"
                      "Father,Mother,Spouses,Children,Gender,Bio",
        }

        try:
            resp = await self._client.post(WIKITREE_API, data=data)
            resp.raise_for_status()
            result = resp.json()
        except Exception:
            return None

        # Navigate to the profile data
        profiles = result if isinstance(result, list) else [result]
        for profile in profiles:
            if isinstance(profile, dict):
                person = profile.get("profile", profile)
                return self._parse_person(person)

        return None
