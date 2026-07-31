"""User model: authentication, email verification, password reset, and 2FA."""
from __future__ import annotations

import datetime as dt
from typing import Any, TYPE_CHECKING

from flask_login import UserMixin
from sqlalchemy import JSON as SAJSON
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from models import db

if TYPE_CHECKING:
    from models.team_membership import TeamMembership


class User(db.Model, UserMixin):
    """A registered user. UserMixin supplies the Flask-Login interface (get_id, etc.)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # --- Email verification ---
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_token: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    verification_sent_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    # --- Password reset ---
    reset_token: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    reset_sent_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    # --- Two-factor authentication (TOTP) ---
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Hashed single-use recovery codes (never stored in plain text), consumed on use.
    totp_recovery_codes: Mapped[list[str] | None] = mapped_column(SAJSON, nullable=True, default=list)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False)

    team_memberships: Mapped[list["TeamMembership"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"<User id={self.id} email={self.email!r}>"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "is_verified": self.is_verified,
            "totp_enabled": self.totp_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
