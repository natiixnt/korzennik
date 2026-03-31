from pydantic import BaseModel


class RelationshipCreate(BaseModel):
    person1_id: str
    person2_id: str
    rel_type: str  # "parent_child" (person1=parent) | "spouse"
    confidence: float = 1.0
    source: str | None = None


class RelationshipOut(BaseModel):
    id: int
    person1_id: str
    person2_id: str
    rel_type: str
    confidence: float
    source: str | None

    model_config = {"from_attributes": True}
