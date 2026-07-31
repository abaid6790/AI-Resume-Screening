"""
Audit logging.

`log()` is deliberately best-effort: a failure to write an audit row should
never break the action being audited (e.g. a resume delete should still
succeed even if, somehow, the audit insert fails). Errors are logged, not
raised.
"""
from __future__ import annotations

import logging

from flask import request

from models import AuditLog, db

logger = logging.getLogger(__name__)


def log(
    action: str,
    description: str | None = None,
    user=None,
    team_id: int | None = None,
) -> None:
    """Record one audit event. Safe to call from any route or service."""
    try:
        entry = AuditLog(
            team_id=team_id,
            user_id=user.id if user is not None else None,
            user_email=user.email if user is not None else None,
            action=action,
            description=description,
            ip_address=request.remote_addr if request else None,
        )
        db.session.add(entry)
        db.session.commit()
    except Exception as exc:  # noqa: BLE001 - logging must never break the caller
        logger.error("Failed to write audit log entry (action=%s): %s", action, exc)
        db.session.rollback()
