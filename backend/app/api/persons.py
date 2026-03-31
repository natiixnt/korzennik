"""CRUD endpoints for persons."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Person, PersonEvent, PersonName
from ..schemas.person import PersonCreate, PersonOut, PersonUpdate

router = APIRouter(prefix="/api/persons", tags=["persons"])


@router.post("", response_model=PersonOut, status_code=201)
async def create_person(data: PersonCreate, db: AsyncSession = Depends(get_db)):
    person = Person(
        gender=data.gender,
        is_living=data.is_living,
        notes=data.notes,
        origin="user_entered",
    )
    db.add(person)
    await db.flush()

    for name_data in data.names:
        name = PersonName(
            person_id=person.id,
            name_type=name_data.name_type,
            given_name=name_data.given_name,
            surname=name_data.surname,
            prefix=name_data.prefix,
            suffix=name_data.suffix,
            is_primary=name_data.is_primary,
        )
        db.add(name)

    for event_data in data.events:
        event = PersonEvent(
            person_id=person.id,
            event_type=event_data.event_type,
            date_text=event_data.date_text,
            date_year=event_data.date_year,
            place_text=event_data.place_text,
            description=event_data.description,
        )
        db.add(event)

    await db.commit()

    # Reload with relationships
    stmt = (
        select(Person)
        .where(Person.id == person.id)
        .options(selectinload(Person.names), selectinload(Person.events))
    )
    result = await db.execute(stmt)
    return result.scalar_one()


@router.get("", response_model=list[PersonOut])
async def list_persons(db: AsyncSession = Depends(get_db)):
    stmt = select(Person).options(
        selectinload(Person.names), selectinload(Person.events)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{person_id}", response_model=PersonOut)
async def get_person(person_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Person)
        .where(Person.id == person_id)
        .options(selectinload(Person.names), selectinload(Person.events))
    )
    result = await db.execute(stmt)
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


@router.put("/{person_id}", response_model=PersonOut)
async def update_person(
    person_id: str, data: PersonUpdate, db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Person)
        .where(Person.id == person_id)
        .options(selectinload(Person.names), selectinload(Person.events))
    )
    result = await db.execute(stmt)
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    if data.gender is not None:
        person.gender = data.gender
    if data.is_living is not None:
        person.is_living = data.is_living
    if data.notes is not None:
        person.notes = data.notes

    await db.commit()
    await db.refresh(person)
    return person


@router.delete("/{person_id}", status_code=204)
async def delete_person(person_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Person).where(Person.id == person_id)
    result = await db.execute(stmt)
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    await db.delete(person)
    await db.commit()
