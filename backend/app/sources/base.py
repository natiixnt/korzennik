"""Base protocol for genealogical data sources."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class SourceRecord:
    """A single record returned by a genealogical data source."""
    source_name: str
    source_record_id: str
    source_url: str | None = None
    given_name: str | None = None
    surname: str | None = None
    birth_date: str | None = None
    birth_year: int | None = None
    birth_place: str | None = None
    death_date: str | None = None
    death_year: int | None = None
    death_place: str | None = None
    father_name: str | None = None
    mother_name: str | None = None
    event_type: str | None = None
    raw_data: dict = field(default_factory=dict)


@runtime_checkable
class GenealogySource(Protocol):
    name: str

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
    ) -> list[SourceRecord]: ...

    async def get_record_detail(self, record_id: str) -> SourceRecord | None: ...
