from pydantic import BaseModel


class PersonNameIn(BaseModel):
    name_type: str = "birth"
    given_name: str | None = None
    surname: str | None = None
    prefix: str | None = None
    suffix: str | None = None
    is_primary: bool = True


class PersonEventIn(BaseModel):
    event_type: str
    date_text: str | None = None
    date_year: int | None = None
    place_text: str | None = None
    description: str | None = None


class PersonCreate(BaseModel):
    gender: str | None = None
    is_living: bool = False
    notes: str | None = None
    names: list[PersonNameIn] = []
    events: list[PersonEventIn] = []


class PersonUpdate(BaseModel):
    gender: str | None = None
    is_living: bool | None = None
    notes: str | None = None


class PersonNameOut(BaseModel):
    id: int
    name_type: str
    given_name: str | None
    surname: str | None
    prefix: str | None
    suffix: str | None
    is_primary: bool

    model_config = {"from_attributes": True}


class PersonEventOut(BaseModel):
    id: int
    event_type: str
    date_text: str | None
    date_year: int | None
    place_text: str | None
    place_normalized: str | None
    description: str | None

    model_config = {"from_attributes": True}


class PersonOut(BaseModel):
    id: str
    origin: str
    gender: str | None
    is_living: bool
    notes: str | None
    names: list[PersonNameOut] = []
    events: list[PersonEventOut] = []

    model_config = {"from_attributes": True}
