"""Dashboard blueprint: landing page with summary stats and charts."""
from __future__ import annotations

import logging

from flask import Blueprint, g, render_template
from sqlalchemy import func

from models import JobDescription, RecommendationEnum, Resume, ScreeningResult, db

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index() -> str:
    """
    Render the main dashboard with live counts scoped to the current team.

    "Candidates screened" counts results that have a completed recommendation
    (excludes Pending/Failed); "average match score" is computed only over
    results that actually have a numeric score. ScreeningResult has no
    team_id of its own, so every screening query joins through
    JobDescription (which does) to stay team-scoped.
    """
    team_id = g.current_team.id

    total_resumes = (
        db.session.scalar(db.select(func.count(Resume.id)).where(Resume.team_id == team_id)) or 0
    )

    screened_query = (
        ScreeningResult.query.join(JobDescription)
        .filter(
            JobDescription.team_id == team_id,
            ScreeningResult.recommendation.in_(
                [RecommendationEnum.SHORTLIST, RecommendationEnum.REVIEW, RecommendationEnum.REJECT]
            ),
        )
    )
    candidates_screened = screened_query.count()

    average_score = db.session.scalar(
        db.select(func.avg(ScreeningResult.match_score))
        .join(JobDescription, ScreeningResult.job_description_id == JobDescription.id)
        .where(JobDescription.team_id == team_id, ScreeningResult.match_score.isnot(None))
    )
    average_score = round(average_score) if average_score is not None else 0

    recent_resumes = (
        Resume.query.filter_by(team_id=team_id).order_by(Resume.uploaded_at.desc()).limit(5).all()
    )
    recent_uploads = []
    for resume in recent_resumes:
        latest_result = (
            ScreeningResult.query.filter_by(resume_id=resume.id)
            .order_by(ScreeningResult.created_at.desc())
            .first()
        )
        recent_uploads.append(
            {
                "resume_id": resume.id,
                "name": resume.candidate_name or resume.filename,
                "uploaded_at": resume.uploaded_at.strftime("%Y-%m-%d %H:%M"),
                "score": latest_result.match_score if latest_result else "—",
                "recommendation": latest_result.recommendation.value if latest_result else "Pending",
            }
        )

    stats = {
        "total_resumes": total_resumes,
        "candidates_screened": candidates_screened,
        "average_score": average_score,
        "recent_uploads": recent_uploads,
        "chart_data": {
            "score_distribution": _score_distribution(team_id),
            "recommendations": _recommendation_breakdown(team_id),
        },
    }
    logger.debug("Rendering dashboard with live stats: %s", stats)
    return render_template("dashboard/index.html", stats=stats)


def _score_distribution(team_id: int) -> dict[str, list]:
    """Bucket every scored result (this team only) into 5 score bands for the histogram."""
    buckets = [(0, 20), (21, 40), (41, 60), (61, 80), (81, 100)]
    labels = ["0-20", "21-40", "41-60", "61-80", "81-100"]
    counts = [0] * len(buckets)

    scores = db.session.scalars(
        db.select(ScreeningResult.match_score)
        .join(JobDescription, ScreeningResult.job_description_id == JobDescription.id)
        .where(JobDescription.team_id == team_id, ScreeningResult.match_score.isnot(None))
    ).all()
    for score in scores:
        for i, (low, high) in enumerate(buckets):
            if low <= score <= high:
                counts[i] += 1
                break

    return {"labels": labels, "counts": counts}


def _recommendation_breakdown(team_id: int) -> dict[str, list]:
    """Count results (this team only) in each of the three core recommendation buckets."""
    labels = ["Shortlist", "Review", "Reject"]
    counts = [
        ScreeningResult.query.join(JobDescription)
        .filter(JobDescription.team_id == team_id, ScreeningResult.recommendation == RecommendationEnum(label))
        .count()
        for label in labels
    ]
    return {"labels": labels, "counts": counts}


@dashboard_bp.route("/health")
def health() -> dict[str, str]:
    """Simple health-check endpoint for uptime monitoring / smoke tests."""
    return {"status": "ok"}
