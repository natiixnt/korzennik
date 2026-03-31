"""FamilySearch API adapter.

Uses the public Person Search endpoint which supports unauthenticated sessions.
API docs: https://www.familysearch.org/developers/docs/api/tree/Person_Search_resource
"""

from __future__ import annotations

import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from .base import SourceRecord

logger = logging.getLogger(__name__)

FS_BASE = "https://api.familysearch.org"
FS_TOKEN_URL = f"{FS_BASE}/cis-web/oauth2/v3/token"
FS_SEARCH_URL = f"{FS_BASE}/platform/tree/search"


class FamilySearchSource:
    name = "familysearch"

    def __init__(self):
        self._token: str | None = None
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _ensure_token(self):
        """Get an unauthenticated session token."""
        if self._token:
            return
        if not settings.familysearch_app_key:
            logger.warning("No FamilySearch app key configured, skipping")
            return
        resp = await self._client.post(
            FS_TOKEN_URL,
            data={
                "grant_type": "unauthenticated_session",
                "client_id": settings.familysearch_app_key,
            },
        )
        resp.raise_for_status()
        self._token = resp.json().get("access_token")

    def _build_query(
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
    ) -> dict[str, str]:
        """Build FamilySearch query parameters."""
        params: dict[str, str] = {}
        if surname:
            params["q.surname"] = surname
        if given_name:
            params["q.givenName"] = given_name
        if birth_year:
            params["q.birthLikeDate"] = f"{birth_year}~"  # ~ = approximate
        if birth_place:
            params["q.birthLikePlace"] = birth_place
        if death_year:
            params["q.deathLikeDate"] = f"{death_year}~"
        if father_given_name:
            params["q.fatherGivenName"] = father_given_name
        if father_surname:
            params["q.fatherSurname"] = father_surname
        if mother_given_name:
            params["q.motherGivenName"] = mother_given_name
        if mother_surname:
            params["q.motherSurname"] = mother_surname
        params["count"] = "50"
        return params

    def _parse_entry(self, entry: dict) -> SourceRecord | None:
        """Parse a single GedcomX search result entry into a SourceRecord."""
        content = entry.get("content", {})
        gedcomx = content.get("gedcomx", {})
        persons = gedcomx.get("persons", [])
        if not persons:
            return None

        person = persons[0]
        pid = person.get("id", "")

        # Extract display info
        display = person.get("display", {})
        given = display.get("name", "").split(" ")[0] if display.get("name") else None
        surname_val = display.get("name", "").split(" ")[-1] if display.get("name") else None
        # Try to get structured name
        names = person.get("names", [])
        if names:
            name_forms = names[0].get("nameForms", [])
            if name_forms:
                parts = name_forms[0].get("parts", [])
                for part in parts:
                    if part.get("type", "").endswith("Given"):
                        given = part.get("value")
                    elif part.get("type", "").endswith("Surname"):
                        surname_val = part.get("value")

        birth_date = display.get("birthDate")
        birth_place = display.get("birthPlace")
        death_date = display.get("deathDate")
        death_place = display.get("deathPlace")

        # Parse year from date string
        birth_year = None
        if birth_date:
            for part in birth_date.split():
                if part.isdigit() and len(part) == 4:
                    birth_year = int(part)
                    break

        death_year = None
        if death_date:
            for part in death_date.split():
                if part.isdigit() and len(part) == 4:
                    death_year = int(part)
                    break

        # Extract parent names from relationships
        father_name = None
        mother_name = None
        relationships = gedcomx.get("relationships", [])
        for rel in relationships:
            rel_type = rel.get("type", "")
            if "ParentChild" in rel_type:
                person1 = rel.get("person1", {})
                # Check if person1 is the parent
                p1_id = person1.get("resourceId", "")
                if p1_id != pid:
                    # person1 is a parent
                    p1_display = None
                    for p in persons[1:]:
                        if p.get("id") == p1_id:
                            p1_display = p.get("display", {})
                            break
                    if p1_display:
                        gender = p1_display.get("gender")
                        name = p1_display.get("name", "")
                        if gender == "Male":
                            father_name = name
                        elif gender == "Female":
                            mother_name = name

        source_url = f"https://www.familysearch.org/tree/person/details/{pid}"

        return SourceRecord(
            source_name=self.name,
            source_record_id=pid,
            source_url=source_url,
            given_name=given,
            surname=surname_val,
            birth_date=birth_date,
            birth_year=birth_year,
            birth_place=birth_place,
            death_date=death_date,
            death_year=death_year,
            death_place=death_place,
            father_name=father_name,
            mother_name=mother_name,
            raw_data=entry,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
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
        await self._ensure_token()
        if not self._token:
            return []

        params = self._build_query(
            given_name=given_name,
            surname=surname,
            birth_year=birth_year,
            birth_place=birth_place,
            death_year=death_year,
            father_given_name=father_given_name,
            father_surname=father_surname,
            mother_given_name=mother_given_name,
            mother_surname=mother_surname,
        )

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/x-gedcomx-atom+json",
        }

        resp = await self._client.get(FS_SEARCH_URL, params=params, headers=headers)
        if resp.status_code == 401:
            # Token expired, refresh
            self._token = None
            await self._ensure_token()
            headers["Authorization"] = f"Bearer {self._token}"
            resp = await self._client.get(FS_SEARCH_URL, params=params, headers=headers)

        resp.raise_for_status()
        data = resp.json()

        results = []
        for entry in data.get("entries", []):
            record = self._parse_entry(entry)
            if record:
                results.append(record)

        logger.info(
            "FamilySearch returned %d results for %s %s",
            len(results), given_name, surname,
        )
        return results

    async def get_record_detail(self, record_id: str) -> SourceRecord | None:
        """Fetch full detail for a specific FamilySearch person."""
        await self._ensure_token()
        if not self._token:
            return None

        url = f"{FS_BASE}/platform/tree/persons/{record_id}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/x-gedcomx-v1+json",
        }
        resp = await self._client.get(url, headers=headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        persons = data.get("persons", [])
        if not persons:
            return None

        person = persons[0]
        display = person.get("display", {})
        return SourceRecord(
            source_name=self.name,
            source_record_id=record_id,
            source_url=f"https://www.familysearch.org/tree/person/details/{record_id}",
            given_name=display.get("name", "").split(" ")[0],
            surname=display.get("name", "").split(" ")[-1],
            birth_date=display.get("birthDate"),
            birth_place=display.get("birthPlace"),
            death_date=display.get("deathDate"),
            death_place=display.get("deathPlace"),
            raw_data=data,
        )
