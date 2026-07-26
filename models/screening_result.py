"""ScreeningResult model: the AI's evaluation of one resume against one job description."""
from __future__ import annotations

import datetime as dt
from typing import Any, TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy import JSON as SAJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import db
from models.enums import RecommendationEnum

if TYPE_CHECKING:
    from models.job_description import JobDescription
    from models.resume import Resume


class ScreeningResult(db.Model):
    """
    One AI screening run: a single resume scored against a single job
    description. A resume may have several of these (one per job it was
    screened against, or re-runs over time) — the most recent one per
    (resume, job_description) pair is what the UI should show by default.
    """

    __tablename__ = "screening_results"
    __table_args__ = (
        CheckConstraint("match_score >= 0 AND match_score <= 100", name="ck_match_score_range"),
        Index("ix_screening_resume_job", "resume_id", "job_description_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    job_description_id: Mapped[int] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False
    )

    match_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    extracted_skills: Mapped[list[str] | None] = mapped_column(SAJSON, nullable=True, default=list)
    extracted_education: Mapped[list[dict] | None] = mapped_column(SAJSON, nullable=True, default=list)
    extracted_experience: Mapped[list[dict] | None] = mapped_column(SAJSON, nullable=True, default=list)
    matching_skills: Mapped[list[str] | None] = mapped_column(SAJSON, nullable=True, default=list)
    missing_skills: Mapped[list[str] | None] = mapped_column(SAJSON, nullable=True, default=list)

    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[RecommendationEnum] = mapped_column(
        db.Enum(RecommendationEnum, native_enum=False, length=20),
        default=RecommendationEnum.PENDING,
        nullable=False,
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow, nullable=False
    )

    resume: Mapped["Resume"] = relationship(back_populates="screening_results")
    job_description: Mapped["JobDescription"] = relationship(back_populates="screening_results")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return (
            f"<ScreeningResult id={self.id} resume_id={self.resume_id} "
            f"job_description_id={self.job_description_id} score={self.match_score}>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict for API/template use."""
        return {
            "id": self.id,
            "resume_id": self.resume_id,
            "job_description_id": self.job_description_id,
            "match_score": self.match_score,
            "extracted_skills": self.extracted_skills or [],
            "extracted_education": self.extracted_education or [],
            "extracted_experience": self.extracted_experience or [],
            "matching_skills": self.matching_skills or [],
            "missing_skills": self.missing_skills or [],
            "explanation": self.explanation,
            "recommendation": self.recommendation.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
