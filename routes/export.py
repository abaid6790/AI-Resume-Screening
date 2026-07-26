"""Export blueprint: CSV and PDF export of a job description's screening results."""
from __future__ import annotations

import logging

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for

from models import JobDescription, ScreeningResult
from services.export_service import export_results_csv, export_results_pdf

logger = logging.getLogger(__name__)

export_bp = Blueprint("export", __name__)


@export_bp.route("/")
def index() -> str:
    """Pick a job description whose results you want to export."""
    jobs = JobDescription.query.order_by(JobDescription.created_at.desc()).all()
    return render_template("export/index.html", jobs=jobs)


def _selected_results(job_id: int) -> tuple[JobDescription, list[ScreeningResult]]:
    """
    Resolve the job and the results to export.

    If a `result_ids` query param is present (comma-separated), export only
    those — this is how the results page exports exactly what's currently
    search/filtered on screen. Otherwise export every result for the job.
    """
    job = JobDescription.query.get_or_404(job_id)

    query = ScreeningResult.query.filter_by(job_description_id=job_id)
    raw_ids = request.args.get("result_ids", "").strip()
    if raw_ids:
        try:
            ids = [int(part) for part in raw_ids.split(",") if part.strip()]
        except ValueError:
            ids = []
        if ids:
            query = query.filter(ScreeningResult.id.in_(ids))

    results = query.order_by(ScreeningResult.match_score.desc()).all()
    return job, results


@export_bp.route("/csv/<int:job_id>")
def export_csv(job_id: int):
    """Download the (optionally filtered) results for one job as CSV."""
    job, results = _selected_results(job_id)
    if not results:
        flash("No results to export for the current selection.", "error")
        return redirect(url_for("screening.results", job_id=job_id))

    filepath = export_results_csv(job, results)
    logger.info("CSV export requested for job_id=%s (%d rows)", job_id, len(results))
    return send_file(filepath, as_attachment=True, download_name=filepath.name)


@export_bp.route("/pdf/<int:job_id>")
def export_pdf(job_id: int):
    """Download the (optionally filtered) results for one job as a formatted PDF."""
    job, results = _selected_results(job_id)
    if not results:
        flash("No results to export for the current selection.", "error")
        return redirect(url_for("screening.results", job_id=job_id))

    filepath = export_results_pdf(job, results)
    logger.info("PDF export requested for job_id=%s (%d rows)", job_id, len(results))
    return send_file(filepath, as_attachment=True, download_name=filepath.name)
