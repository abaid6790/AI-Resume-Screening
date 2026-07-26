"""Resume model: one uploaded PDF and the text extracted from it."""
from __future__ import annotations

import datetime as dt
from typing import Any, TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import db
from models.enums import ExtractionStatus

if TYPE_CHECKING:
    from models.screening_result import ScreeningResult


class Resume(db.Model):
    """
    A single uploaded resume file.

    Deliberately NOT tied to one job_description_id: the same resume can be
    screened against multiple job descriptions over time. That link lives on
    ScreeningResult instead, so a resume is uploaded once and reused.
    """

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Original uploaded filename and the path it was stored at on disk.
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    filepath: Mapped[str] = mapped_column(String(500), nullable=False)

    # Best-effort candidate identity, refined by AI extraction in Phase 4.
    candidate_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        db.Enum(ExtractionStatus, native_enum=False, length=20),
        default=ExtractionStatus.PENDING,
        nullable=False,
    )
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    uploaded_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow, nullable=False
    )

    screening_results: Mapped[list["ScreeningResult"]] = relationship(
        back_populates="resume",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"<Resume id={self.id} filename={self.filename!r}>"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict for API/template use."""
        return {
            "id": self.id,
            "filename": self.filename,
            "candidate_name": self.candidate_name,
            "candidate_email": self.candidate_email,
            "extraction_status": self.extraction_status.value,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }
