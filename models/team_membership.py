"""TeamMembership model: a (user, team, role) triple."""
from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import db
from models.enums import TeamRole

if TYPE_CHECKING:
    from models.team import Team
    from models.user import User


class TeamMembership(db.Model):
    """One user's role within one team. A user may belong to several teams."""

    __tablename__ = "team_memberships"
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[TeamRole] = mapped_column(
        db.Enum(TeamRole, native_enum=False, length=20), default=TeamRole.MEMBER, nullable=False
    )
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False)

    team: Mapped["Team"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="team_memberships")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"<TeamMembership team_id={self.team_id} user_id={self.user_id} role={self.role.value}>"
