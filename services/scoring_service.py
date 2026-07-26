"""
Screening orchestration: calls the Gemini service, resolves the final
recommendation (falling back to score-threshold logic if Gemini's own
recommendation is missing or invalid), and persists a ScreeningResult.
"""
from __future__ import annotations

import logging

from flask import current_app

from models import JobDescription, RecommendationEnum, Resume, ScreeningResult, db
from services.gemini_service import GeminiServiceError, screen_resume_with_gemini

logger = logging.getLogger(__name__)


def screen_resume(resume: Resume, job: JobDescription) -> ScreeningResult:
    """
    Screen one resume against one job description and persist the result.

    Never raises: API/parsing failures are captured as a ScreeningResult with
    recommendation=FAILED so one bad resume or API hiccup doesn't kill a batch run.
    """
    try:
        data = screen_resume_with_gemini(resume.raw_text or "", job.raw_text)
    except GeminiServiceError as exc:
        logger.error("Screening failed for resume_id=%s job_id=%s: %s", resume.id, job.id, exc)
        result = ScreeningResult(
            resume_id=resume.id,
            job_description_id=job.id,
            recommendation=RecommendationEnum.FAILED,
            explanation=f"AI screening failed: {exc}",
        )
        db.session.add(result)
        db.session.commit()
        return result

    recommendation = _resolve_recommendation(data.get("recommendation"), data.get("match_score"))

    result = ScreeningResult(
        resume_id=resume.id,
        job_description_id=job.id,
        match_score=data.get("match_score"),
        extracted_skills=data.get("extracted_skills") or [],
        extracted_education=data.get("extracted_education") or [],
        extracted_experience=data.get("extracted_experience") or [],
        matching_skills=data.get("matching_skills") or [],
        missing_skills=data.get("missing_skills") or [],
        explanation=data.get("explanation"),
        recommendation=recommendation,
    )
    db.session.add(result)

    # Fill in the candidate's name if our upload-time heuristic missed it
    # but Gemini's structured extraction found one.
    if not resume.candidate_name and data.get("candidate_name"):
        resume.candidate_name = data["candidate_name"]

    db.session.commit()
    logger.info(
        "Screened resume_id=%s job_id=%s score=%s recommendation=%s",
        resume.id, job.id, result.match_score, result.recommendation.value,
    )
    return result


def _resolve_recommendation(value: str | None, score: int | None) -> RecommendationEnum:
    """Trust Gemini's recommendation if it's valid; otherwise derive it from score thresholds."""
    if value:
        try:
            return RecommendationEnum(value)
        except ValueError:
            pass

    if score is None:
        return RecommendationEnum.REVIEW

    shortlist_threshold = current_app.config.get("SHORTLIST_THRESHOLD", 75)
    review_threshold = current_app.config.get("REVIEW_THRESHOLD", 50)

    if score >= shortlist_threshold:
        return RecommendationEnum.SHORTLIST
    if score >= review_threshold:
        return RecommendationEnum.REVIEW
    return RecommendationEnum.REJECT
