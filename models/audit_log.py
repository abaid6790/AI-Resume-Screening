"""AuditLog model: a record of who did what, when."""
from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import db


class AuditLog(db.Model):
    """
    An append-only log entry. `team_id`/`user_id` are nullable so
    account-level events that happen before a user has a team context (or
    after a user is deleted) can still be recorded rather than dropped.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True)  # kept even if the user is later deleted

    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False, index=True)

    team = relationship("Team")
    user = relationship("User")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"<AuditLog id={self.id} action={self.action!r} user={self.user_email!r}>"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "description": self.description,
            "user_email": self.user_email,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
