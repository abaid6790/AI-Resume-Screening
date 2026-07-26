"""Resume blueprint: multi-file upload, storage, text extraction, and management."""
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

from models import Resume, db
from services.resume_service import (
    ResumeServiceError,
    extract_candidate_email,
    extract_candidate_name,
    extract_text_from_pdf,
)

logger = logging.getLogger(__name__)

resumes_bp = Blueprint("resumes", __name__)


@resumes_bp.route("/")
def index() -> str:
    """List all uploaded resumes, most recent first."""
    resumes = Resume.query.order_by(Resume.uploaded_at.desc()).all()
    return render_template("resumes/index.html", resumes=resumes)


@resumes_bp.route("/upload", methods=["GET", "POST"])
def upload():
    """Show the drag-and-drop upload form (GET) or ingest resume files (POST)."""
    if request.method == "GET":
        return render_template("resumes/upload.html")

    files = [f for f in request.files.getlist("resume_files") if f and f.filename]
    if not files:
        flash("Choose at least one PDF resume to upload.", "error")
        return redirect(url_for("resumes.upload"))

    saved: list[Resume] = []
    skipped: list[tuple[str, str]] = []

    for file in files:
        try:
            resume = _save_and_process(file)
            saved.append(resume)
        except ResumeServiceError as exc:
            logger.warning("Resume upload skipped for %r: %s", file.filename, exc)
            skipped.append((file.filename or "unknown file", str(exc)))

    if saved:
        flash(f"Uploaded {len(saved)} resume(s) successfully.", "success")
    for filename, reason in skipped:
        flash(f'"{filename}" was not uploaded: {reason}', "error")

    return redirect(url_for("resumes.index"))


@resumes_bp.route("/<int:resume_id>")
def detail(resume_id: int):
    """Show one resume's extraction status, guessed identity, and raw text."""
    resume = Resume.query.get_or_404(resume_id)
    return render_template("resumes/detail.html", resume=resume)


@resumes_bp.route("/<int:resume_id>/delete", methods=["POST"])
def delete(resume_id: int):
    """Delete a resume record (cascades screening results) and its file on disk."""
    resume = Resume.query.get_or_404(resume_id)
    filepath = Path(resume.filepath)
    filename = resume.filename

    db.session.delete(resume)
    db.session.commit()

    if filepath.exists():
        try:
            filepath.unlink()
        except OSError as exc:
            logger.warning("Could not remove resume file %s: %s", filepath, exc)

    logger.info("Deleted resume id=%s filename=%r", resume_id, filename)
    flash(f'Deleted "{filename}".', "success")
    return redirect(url_for("resumes.index"))


def _save_and_process(upload: FileStorage) -> Resume:
    """Validate, store on disk, extract text, and persist one resume. Raises ResumeServiceError."""
    filename = secure_filename(upload.filename or "")
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed = current_app.config["ALLOWED_RESUME_EXTENSIONS"]

    if not filename or extension not in allowed:
        raise ResumeServiceError(f'Unsupported file type ".{extension}". Only PDF is accepted.')

    resumes_folder = Path(current_app.config["UPLOAD_FOLDER"]) / "resumes"
    resumes_folder.mkdir(parents=True, exist_ok=True)
    stored_path = resumes_folder / f"{uuid.uuid4().hex}_{filename}"
    upload.save(stored_path)

    text, status, error = extract_text_from_pdf(stored_path)

    resume = Resume(
        filename=filename,
        filepath=str(stored_path),
        candidate_name=extract_candidate_name(text) if text else None,
        candidate_email=extract_candidate_email(text) if text else None,
        raw_text=text,
        extraction_status=status,
        extraction_error=error,
    )
    db.session.add(resume)
    db.session.commit()
    logger.info(
        "Uploaded resume id=%s filename=%r status=%s", resume.id, filename, status.value
    )
    return resume
