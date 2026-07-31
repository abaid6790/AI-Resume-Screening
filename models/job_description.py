"""JobDescription model: a saved/reusable job posting recruiters screen resumes against."""
from __future__ import annotations

import datetime as dt
from typing import Any, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import JSON as SAJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import db

if TYPE_CHECKING:
    from models.screening_result import ScreeningResult
    from models.team import Team


class JobDescription(db.Model):
    """A job description, pasted or uploaded, that can be reused across screening runs."""

    __tablename__ = "job_descriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Required skills/keywords parsed out of raw_text. Populated by a simple
    # keyword pass in Phase 2 and refined by Gemini in Phase 4.
    parsed_skills: Mapped[list[str] | None] = mapped_column(
        SAJSON, nullable=True, default=list
    )

    # Set only if the JD was uploaded as a file rather than pasted as text.
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow, nullable=False
    )

    team: Mapped["Team"] = relationship(back_populates="job_descriptions")
    screening_results: Mapped[list["ScreeningResult"]] = relationship(
        back_populates="job_description",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"<JobDescription id={self.id} title={self.title!r}>"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict for API/template use."""
        return {
            "id": self.id,
            "title": self.title,
            "raw_text": self.raw_text,
            "parsed_skills": self.parsed_skills or [],
            "source_filename": self.source_filename,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "screening_count": len(self.screening_results),
        }
