from pydantic import BaseModel


class SearchRequest(BaseModel):
    sources: list[str] | None = None  # None = all available sources


class MatchOut(BaseModel):
    id: int
    person_id: str
    source_name: str
    source_record_id: str
    source_url: str | None
    given_name: str | None
    surname: str | None
    birth_date: str | None
    birth_place: str | None
    death_date: str | None
    death_place: str | None
    father_name: str | None
    mother_name: str | None
    confidence_score: float
    confidence_breakdown: dict | None = None
    status: str

    model_config = {"from_attributes": True}


class TaskStatusOut(BaseModel):
    id: int
    source_name: str
    status: str
    result_count: int
    error_message: str | None

    model_config = {"from_attributes": True}
