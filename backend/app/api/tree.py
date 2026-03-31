"""Tree visualization endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..schemas.tree import TreeNode
from ..services.tree_builder import build_tree

router = APIRouter(prefix="/api/tree", tags=["tree"])


@router.get("", response_model=list[TreeNode])
async def get_tree(db: AsyncSession = Depends(get_db)):
    """Get full tree in family-chart compatible format."""
    return await build_tree(db)
