import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Person(Base):
    __tablename__ = "persons"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    origin: Mapped[str] = mapped_column(String, default="user_entered")
    gender: Mapped[str | None] = mapped_column(String, nullable=True)
    is_living: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, onupdate=func.now(), nullable=True
    )

    names: Mapped[list["PersonName"]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )
    events: Mapped[list["PersonEvent"]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )


class PersonName(Base):
    __tablename__ = "person_names"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("persons.id"), index=True)
    name_type: Mapped[str] = mapped_column(String, default="birth")
    given_name: Mapped[str | None] = mapped_column(String, nullable=True)
    surname: Mapped[str | None] = mapped_column(String, nullable=True)
    prefix: Mapped[str | None] = mapped_column(String, nullable=True)
    suffix: Mapped[str | None] = mapped_column(String, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)

    person: Mapped["Person"] = relationship(back_populates="names")


class PersonEvent(Base):
    __tablename__ = "person_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("persons.id"), index=True)
    event_type: Mapped[str] = mapped_column(String)
    date_text: Mapped[str | None] = mapped_column(String, nullable=True)
    date_sort: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    place_text: Mapped[str | None] = mapped_column(String, nullable=True)
    place_normalized: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    person: Mapped["Person"] = relationship(back_populates="events")
