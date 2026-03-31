"""Geneanet adapter.

9+ billion records with very strong European coverage.
Searches public family trees and indexed historical records.
"""

from __future__ import annotations

import logging
import re

import httpx
from selectolax.parser import HTMLParser

from .base import SourceRecord
from .scraper_base import BaseHTMLScraper

logger = logging.getLogger(__name__)

GENEANET_SEARCH = "https://en.geneanet.org/fonds/individus/"


class GeneanetSource(BaseHTMLScraper):
    name = "geneanet"
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

        params: dict[str, str] = {
            "nom": surname,
            "ignore_each": "0",
        }
        if given_name:
            params["prenom"] = given_name
        if birth_year:
            params["annee_naissance"] = str(birth_year)
            params["precision_naissance"] = "5"
        if birth_place:
            params["lieu_naissance"] = birth_place
        if death_year:
            params["annee_deces"] = str(death_year)
            params["precision_deces"] = "5"

        resp = await self.fetch(GENEANET_SEARCH, params)
        if not resp:
            return []

        results = self._parse_results(resp.text)
        logger.info("Geneanet returned %d results for %s %s", len(results), given_name, surname)
        return results

    def _parse_results(self, html: str) -> list[SourceRecord]:
        tree = HTMLParser(html)
        results = []

        # Geneanet uses various result card formats
        cards = tree.css(
            "div.search_result, div.ligne_resultat, "
            "li.item, div.result-item, tr.result"
        )

        for card in cards[:self.max_results]:
            record = self._parse_card(card)
            if record:
                results.append(record)

        return results

    def _parse_card(self, card) -> SourceRecord | None:
        link = card.css_first("a[href*='/arbre/']")
        if not link:
            link = card.css_first("a[href]")
        if not link:
            return None

        href = link.attributes.get("href", "")
        if not href:
            return None

        # Extract ID from URL
        id_match = re.search(r"p=(\w+)&n=(\w+)", href)
        if id_match:
            record_id = f"{id_match.group(2)}-{id_match.group(1)}"
        else:
            record_id = re.sub(r"[^a-zA-Z0-9]", "", href[-30:])

        if not href.startswith("http"):
            href = f"https://en.geneanet.org{href}"

        # Name
        name_el = card.css_first("a.nom, span.name, .result-name, a")
        full_name = name_el.text(strip=True) if name_el else link.text(strip=True)
        parts = full_name.split()
        given = parts[0] if parts else None
        surname = parts[-1] if len(parts) > 1 else None

        card_text = card.text(strip=True)

        # Extract dates
        birth_year = None
        death_year = None
        birth_place = None

        # Pattern: born YYYY in PLACE
        born_match = re.search(r"(?:born|ne|nee|ur\.?)\s+(?:ca\.?\s+)?(\d{4})", card_text, re.IGNORECASE)
        if born_match:
            birth_year = int(born_match.group(1))

        died_match = re.search(r"(?:died|dcd|dec|zm\.?)\s+(?:ca\.?\s+)?(\d{4})", card_text, re.IGNORECASE)
        if died_match:
            death_year = int(died_match.group(1))

        # Fallback: extract years
        if not birth_year:
            years = re.findall(r"\b(1[4-9]\d{2}|20[0-2]\d)\b", card_text)
            if years:
                birth_year = int(years[0])
                if len(years) > 1 and not death_year:
                    death_year = int(years[1])

        # Place
        place_match = re.search(r"(?:in|a|w)\s+([\w\s,]+?)(?:\s*[-;.]|\s*(?:died|dec|zm))", card_text, re.IGNORECASE)
        if place_match:
            birth_place = place_match.group(1).strip()

        # Parents
        father_name = None
        mother_name = None
        father_match = re.search(r"(?:father|pere|ojciec)\s*:?\s*([\w\s]+?)(?:[,;.]|$)", card_text, re.IGNORECASE)
        if father_match:
            father_name = father_match.group(1).strip()
        mother_match = re.search(r"(?:mother|mere|matka)\s*:?\s*([\w\s]+?)(?:[,;.]|$)", card_text, re.IGNORECASE)
        if mother_match:
            mother_name = mother_match.group(1).strip()

        return SourceRecord(
            source_name=self.name,
            source_record_id=f"gn-{record_id}",
            source_url=href,
            given_name=given,
            surname=surname,
            birth_year=birth_year,
            birth_date=str(birth_year) if birth_year else None,
            birth_place=birth_place,
            death_year=death_year,
            death_date=str(death_year) if death_year else None,
            father_name=father_name,
            mother_name=mother_name,
            event_type="tree",
            raw_data={"full_name": full_name, "card_text": card_text[:300]},
        )

    async def get_record_detail(self, record_id: str) -> SourceRecord | None:
        return None
