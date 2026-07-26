"""Job description blueprint: create, view, list, and delete job descriptions."""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from models import JobDescription, db
from services.jd_service import JDServiceError, extract_skills, extract_text_from_upload

logger = logging.getLogger(__name__)

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.route("/")
def index() -> str:
    """List all saved job descriptions, most recent first."""
    jobs = JobDescription.query.order_by(JobDescription.created_at.desc()).all()
    return render_template("jobs/index.html", jobs=jobs)


@jobs_bp.route("/new", methods=["GET", "POST"])
def new():
    """Show the create form (GET) or save a new job description (POST)."""
    if request.method == "GET":
        return render_template("jobs/new.html")

    title = (request.form.get("title") or "").strip()
    pasted_text = (request.form.get("raw_text") or "").strip()
    upload = request.files.get("jd_file")

    if not title:
        flash("Please give this job description a title.", "error")
        return render_template("jobs/new.html", title=title, raw_text=pasted_text), 400

    raw_text = pasted_text
    source_filename = None

    if upload and upload.filename:
        try:
            raw_text, source_filename = _save_and_extract(upload)
        except JDServiceError as exc:
            logger.warning("JD upload failed for title=%r: %s", title, exc)
            flash(str(exc), "error")
            return render_template("jobs/new.html", title=title, raw_text=pasted_text), 400

    if not raw_text:
        flash("Paste the job description text or upload a file.", "error")
        return render_template("jobs/new.html", title=title, raw_text=pasted_text), 400

    job = JobDescription(
        title=title,
        raw_text=raw_text,
        parsed_skills=extract_skills(raw_text),
        source_filename=source_filename,
    )
    db.session.add(job)
    db.session.commit()
    logger.info("Created job description id=%s title=%r", job.id, job.title)
    flash(f'Saved "{job.title}".', "success")
    return redirect(url_for("jobs.detail", job_id=job.id))


@jobs_bp.route("/<int:job_id>")
def detail(job_id: int):
    """Show one job description with its detected skills."""
    job = JobDescription.query.get_or_404(job_id)
    return render_template("jobs/detail.html", job=job)


@jobs_bp.route("/<int:job_id>/delete", methods=["POST"])
def delete(job_id: int):
    """Delete a job description and its (cascaded) screening results."""
    job = JobDescription.query.get_or_404(job_id)
    title = job.title
    db.session.delete(job)
    db.session.commit()
    logger.info("Deleted job description id=%s title=%r", job_id, title)
    flash(f'Deleted "{title}".', "success")
    return redirect(url_for("jobs.index"))


def _save_and_extract(upload: FileStorage) -> tuple[str, str]:
    """Validate, store, and extract text from an uploaded JD file. Raises JDServiceError."""
    filename = secure_filename(upload.filename or "")
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed = current_app.config["ALLOWED_JD_EXTENSIONS"]

    if not filename or extension not in allowed:
        raise JDServiceError(
            f'Unsupported file type ".{extension}". Allowed: {", ".join(sorted(allowed))}.'
        )

    jd_folder = Path(current_app.config["UPLOAD_FOLDER"]) / "job_descriptions"
    jd_folder.mkdir(parents=True, exist_ok=True)
    stored_path = jd_folder / f"{uuid.uuid4().hex}_{filename}"
    upload.save(stored_path)

    text = extract_text_from_upload(stored_path, extension)
    if not text.strip():
        raise JDServiceError("Could not extract any text from the uploaded file.")
    return text, filename
