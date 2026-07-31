"""
Models package.

`db` is instantiated here (unbound) and attached to the app in the
application factory (`app.py`). Model modules are imported at the bottom
of this file (after `db` exists) so `db.create_all()` and relationship
lookups can see every table, and so other modules can simply do
`from models import JobDescription, Resume, ScreeningResult`.
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Imported after `db` is defined above — each model module does
# `from models import db`, so this order avoids a circular import.
from models.enums import ExtractionStatus, RecommendationEnum, TeamRole  # noqa: E402
from models.team import Team  # noqa: E402
from models.user import User  # noqa: E402
from models.team_membership import TeamMembership  # noqa: E402
from models.job_description import JobDescription  # noqa: E402
from models.resume import Resume  # noqa: E402
from models.screening_result import ScreeningResult  # noqa: E402
from models.audit_log import AuditLog  # noqa: E402

__all__ = [
    "db",
    "ExtractionStatus",
    "RecommendationEnum",
    "TeamRole",
    "Team",
    "TeamMembership",
    "JobDescription",
    "Resume",
    "ScreeningResult",
    "User",
    "AuditLog",
]
