"""
Shared enumerations used across models.

Kept in their own module (rather than inline in each model) so both the
model layer and the service layer (Phases 3-4) can import the same
canonical values without circular imports.
"""
from __future__ import annotations

import enum


class ExtractionStatus(str, enum.Enum):
    """State of PDF -> text extraction for an uploaded resume (Phase 3)."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    NEEDS_OCR = "needs_ocr"


class RecommendationEnum(str, enum.Enum):
    """Outcome of AI screening for a resume against a job description (Phase 4)."""

    PENDING = "Pending"
    SHORTLIST = "Shortlist"
    REVIEW = "Review"
    REJECT = "Reject"
    FAILED = "Failed"


class TeamRole(str, enum.Enum):
    """A user's permission level within one team."""

    OWNER = "owner"    # full control: manage members/roles, cannot be removed
    ADMIN = "admin"     # can invite/remove Members, cannot manage Owner/other Admins
    MEMBER = "member"   # normal app usage, no team-management access
