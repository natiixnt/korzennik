"""Build tree structure from database for frontend visualization."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Person, Relationship
from ..schemas.tree import TreeNode, TreeNodeData, TreeNodeRels


async def build_tree(session: AsyncSession) -> list[TreeNode]:
    """Build full tree in family-chart compatible format."""
    stmt = select(Person).options(
        selectinload(Person.names),
        selectinload(Person.events),
    )
    result = await session.execute(stmt)
    persons = result.scalars().all()
    person_ids = {p.id for p in persons}

    rel_stmt = select(Relationship)
    rel_result = await session.execute(rel_stmt)
    relationships = rel_result.scalars().all()

    # Build relationship maps with deduplication
    spouse_map: dict[str, set[str]] = {}
    parent_map: dict[str, set[str]] = {}  # child_id -> parent_ids
    child_map: dict[str, set[str]] = {}   # parent_id -> child_ids

    for rel in relationships:
        # Skip relationships referencing non-existent persons
        if rel.person1_id not in person_ids or rel.person2_id not in person_ids:
            continue
        # Skip self-references
        if rel.person1_id == rel.person2_id:
            continue

        if rel.rel_type == "spouse":
            spouse_map.setdefault(rel.person1_id, set()).add(rel.person2_id)
            spouse_map.setdefault(rel.person2_id, set()).add(rel.person1_id)
        elif rel.rel_type == "parent_child":
            # person1 = parent, person2 = child
            parent_map.setdefault(rel.person2_id, set()).add(rel.person1_id)
            child_map.setdefault(rel.person1_id, set()).add(rel.person2_id)

    nodes = []
    for person in persons:
        primary_name = next(
            (n for n in person.names if n.is_primary),
            person.names[0] if person.names else None,
        )

        birth = next((e for e in person.events if e.event_type == "birth"), None)
        death = next((e for e in person.events if e.event_type == "death"), None)

        data = TreeNodeData(
            gender=person.gender,
            first_name=primary_name.given_name if primary_name else None,
            last_name=primary_name.surname if primary_name else None,
            birthday=birth.date_text if birth else None,
            deathday=death.date_text if death else None,
            birth_place=birth.place_text if birth else None,
            death_place=death.place_text if death else None,
            origin=person.origin,
        )

        rels = TreeNodeRels(
            spouses=sorted(spouse_map.get(person.id, set())),
            parents=sorted(parent_map.get(person.id, set())),
            children=sorted(child_map.get(person.id, set())),
        )

        nodes.append(TreeNode(id=person.id, data=data, rels=rels))

    return nodes
