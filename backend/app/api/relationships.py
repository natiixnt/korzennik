"""CRUD endpoints for relationships."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Relationship
from ..schemas.relationship import RelationshipCreate, RelationshipOut

router = APIRouter(prefix="/api/relationships", tags=["relationships"])


@router.post("", response_model=RelationshipOut, status_code=201)
async def create_relationship(
    data: RelationshipCreate, db: AsyncSession = Depends(get_db)
):
    # Prevent self-referencing
    if data.person1_id == data.person2_id:
        raise HTTPException(400, "Cannot create relationship with self")

    # Prevent duplicates (check both directions for spouse)
    if data.rel_type == "spouse":
        dup = await db.execute(
            select(Relationship).where(
                Relationship.rel_type == "spouse",
                or_(
                    and_(Relationship.person1_id == data.person1_id, Relationship.person2_id == data.person2_id),
                    and_(Relationship.person1_id == data.person2_id, Relationship.person2_id == data.person1_id),
                ),
            )
        )
    else:
        dup = await db.execute(
            select(Relationship).where(
                Relationship.rel_type == data.rel_type,
                Relationship.person1_id == data.person1_id,
                Relationship.person2_id == data.person2_id,
            )
        )
    if dup.scalar_one_or_none():
        raise HTTPException(409, "Relationship already exists")

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


@router.get("", response_model=list[RelationshipOut])
async def list_all_relationships(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Relationship))
    return result.scalars().all()


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
