"""Team model: the data-isolation boundary for job descriptions and resumes."""
from __future__ import annotations

import datetime as dt
from typing import Any, TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import db

if TYPE_CHECKING:
    from models.job_description import JobDescription
    from models.resume import Resume
    from models.team_membership import TeamMembership


class Team(db.Model):
    """
    A team is what job descriptions/resumes actually belong to, not a user
    directly — this is what makes data isolation real rather than cosmetic.
    Every user gets a personal team automatically on registration and can
    additionally join or create others.
    """

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False)

    memberships: Mapped[list["TeamMembership"]] = relationship(
        back_populates="team", cascade="all, delete-orphan", lazy="selectin"
    )
    job_descriptions: Mapped[list["JobDescription"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    resumes: Mapped[list["Resume"]] = relationship(back_populates="team", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"<Team id={self.id} name={self.name!r}>"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "member_count": len(self.memberships),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
