from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person1_id: Mapped[str] = mapped_column(ForeignKey("persons.id"), index=True)
    person2_id: Mapped[str] = mapped_column(ForeignKey("persons.id"), index=True)
    rel_type: Mapped[str] = mapped_column(String)  # "parent_child" | "spouse"
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
