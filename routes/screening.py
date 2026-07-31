"""AI screening blueprint: select a job + resumes, run Gemini scoring, view results."""
from __future__ import annotations

import logging

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from sqlalchemy import desc, nullslast

from models import JobDescription, Resume, ScreeningResult
from services.scoring_service import screen_resume

logger = logging.getLogger(__name__)

screening_bp = Blueprint("screening", __name__)


@screening_bp.route("/")
def index() -> str:
    """Pick a job description and choose which resumes to screen against it (current team only)."""
    jobs = (
        JobDescription.query.filter_by(team_id=g.current_team.id)
        .order_by(JobDescription.created_at.desc())
        .all()
    )
    resumes = (
        Resume.query.filter_by(team_id=g.current_team.id)
        .order_by(Resume.uploaded_at.desc())
        .all()
    )

    selected_job_id = request.args.get("job_id", type=int)
    selected_job = None
    already_screened_ids: set[int] = set()

    if selected_job_id:
        selected_job = JobDescription.query.filter_by(
            id=selected_job_id, team_id=g.current_team.id
        ).first_or_404()
        already_screened_ids = {
            r.resume_id
            for r in ScreeningResult.query.filter_by(job_description_id=selected_job_id).all()
        }

    return render_template(
        "screening/index.html",
        jobs=jobs,
        resumes=resumes,
        selected_job=selected_job,
        already_screened_ids=already_screened_ids,
    )


@screening_bp.route("/run", methods=["POST"])
def run():
    """Run Gemini screening for the selected resumes against the selected job description."""
    job_id = request.form.get("job_id", type=int)
    resume_ids = request.form.getlist("resume_ids", type=int)

    if not job_id:
        flash("Choose a job description first.", "error")
        return redirect(url_for("screening.index"))

    job = JobDescription.query.filter_by(id=job_id, team_id=g.current_team.id).first_or_404()

    if not resume_ids:
        flash("Choose at least one resume to screen.", "error")
        return redirect(url_for("screening.index", job_id=job_id))

    # team_id filter here matters: without it, a crafted resume_ids list could
    # screen another team's resume against this team's job description.
    resumes = Resume.query.filter(
        Resume.id.in_(resume_ids), Resume.team_id == g.current_team.id
    ).all()

    succeeded, skipped, failed = 0, 0, 0
    for resume in resumes:
        if not resume.raw_text:
            skipped += 1
            logger.info("Skipping resume_id=%s: no extracted text available", resume.id)
            continue
        result = screen_resume(resume, job)
        if result.recommendation.value == "Failed":
            failed += 1
        else:
            succeeded += 1

    if succeeded:
        flash(f'Screened {succeeded} resume(s) against "{job.title}".', "success")
    if failed:
        flash(f"{failed} resume(s) failed AI screening (see individual reports for details).", "error")
    if skipped:
        flash(f"{skipped} resume(s) were skipped — no extracted text available.", "error")

    return redirect(url_for("screening.results", job_id=job.id))


@screening_bp.route("/results/<int:job_id>")
def results(job_id: int):
    """Show all screening results for one job description, best score first."""
    job = JobDescription.query.filter_by(id=job_id, team_id=g.current_team.id).first_or_404()
    job_results = (
        ScreeningResult.query.filter_by(job_description_id=job_id)
        .order_by(nullslast(desc(ScreeningResult.match_score)), desc(ScreeningResult.created_at))
        .all()
    )
    rows = [_build_result_row(r) for r in job_results]
    return render_template("screening/results.html", job=job, rows=rows)


def _build_result_row(result: ScreeningResult) -> dict:
    """Precompute simple derived, sortable fields (years of experience, skill count) for the results table."""
    years = 0.0
    for exp in result.extracted_experience or []:
        try:
            years += float(exp.get("years") or 0)
        except (TypeError, ValueError, AttributeError):
            continue

    return {
        "id": result.id,
        "candidate_name": result.resume.candidate_name or result.resume.filename,
        "match_score": result.match_score,
        "years_experience": years,
        "skills_count": len(result.extracted_skills or []),
        "recommendation": result.recommendation.value,
        "created_at": result.created_at,
    }


@screening_bp.route("/result/<int:result_id>")
def detail(result_id: int):
    """Show one candidate's full evaluation report — 404s if it's not this team's."""
    result = (
        ScreeningResult.query.join(JobDescription)
        .filter(ScreeningResult.id == result_id, JobDescription.team_id == g.current_team.id)
        .first_or_404()
    )
    return render_template("screening/detail.html", result=result)
