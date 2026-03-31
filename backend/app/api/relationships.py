"""CRUD endpoints for relationships."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Relationship
from ..schemas.relationship import RelationshipCreate, RelationshipOut

router = APIRouter(prefix="/api/relationships", tags=["relationships"])


@router.post("", response_model=RelationshipOut, status_code=201)
async def create_relationship(
    data: RelationshipCreate, db: AsyncSession = Depends(get_db)
):
    rel = Relationship(
        person1_id=data.person1_id,
        person2_id=data.person2_id,
        rel_type=data.rel_type,
        confidence=data.confidence,
        source=data.source,
    )
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    return rel


@router.get("/person/{person_id}", response_model=list[RelationshipOut])
async def get_relationships_for_person(
    person_id: str, db: AsyncSession = Depends(get_db)
):
    stmt = select(Relationship).where(
        or_(
            Relationship.person1_id == person_id,
            Relationship.person2_id == person_id,
        )
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.delete("/{rel_id}", status_code=204)
async def delete_relationship(rel_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Relationship).where(Relationship.id == rel_id)
    result = await db.execute(stmt)
    rel = result.scalar_one_or_none()
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found")
    await db.delete(rel)
    await db.commit()
