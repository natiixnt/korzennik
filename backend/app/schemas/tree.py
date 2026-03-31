from pydantic import BaseModel


class TreeNodeData(BaseModel):
    gender: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    birthday: str | None = None
    deathday: str | None = None
    birth_place: str | None = None
    death_place: str | None = None
    confidence: float = 1.0
    origin: str = "user_entered"


class TreeNodeRels(BaseModel):
    spouses: list[str] = []
    parents: list[str] = []
    children: list[str] = []


class TreeNode(BaseModel):
    id: str
    data: TreeNodeData
    rels: TreeNodeRels
