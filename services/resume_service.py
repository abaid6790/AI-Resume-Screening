"""
Resume ingestion helpers: PDF text extraction and simple identity heuristics.

Name/email extraction here is a cheap regex-based placeholder. Phase 4
replaces it with Gemini-based structured extraction (name, education,
experience, skills) — this module just needs to get something reasonable
on screen before that exists.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from models import ExtractionStatus

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# A "name line" is 2-4 capitalized-ish words, letters/hyphens/apostrophes only.
NAME_LINE_RE = re.compile(r"^[A-Za-z][A-Za-z.'-]*(?:\s+[A-Za-z][A-Za-z.'-]*){1,3}$")

# Lines containing these words are section headers/contact info, not a name.
NAME_SKIP_WORDS = {
    "resume", "curriculum", "vitae", "profile", "summary", "objective",
    "contact", "address", "phone", "email", "linkedin", "github", "portfolio",
}


class ResumeServiceError(Exception):
    """Raised for any recoverable error while ingesting a resume file."""


def extract_text_from_pdf(filepath: Path) -> tuple[str | None, ExtractionStatus, str | None]:
    """
    Extract plain text from a PDF resume.

    Returns (text, status, error_message):
      - SUCCESS   -> (text, SUCCESS, None)
      - NEEDS_OCR -> (None, NEEDS_OCR, reason)   -- e.g. a scanned PDF with no text layer
      - FAILED    -> (None, FAILED, reason)      -- e.g. corrupt/unreadable file
    """
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - dependency guard
        logger.error("pdfplumber is not installed: %s", exc)
        return None, ExtractionStatus.FAILED, "PDF support is not installed on the server."

    text_parts: list[str] = []
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
    except Exception as exc:  # noqa: BLE001 - any parser failure becomes a clean status
        logger.warning("Failed to extract text from resume %s: %s", filepath, exc)
        return None, ExtractionStatus.FAILED, f"Could not read the PDF file: {exc}"

    text = "\n".join(text_parts).strip()
    if not text:
        return (
            None,
            ExtractionStatus.NEEDS_OCR,
            "No embedded text layer found — this looks like a scanned PDF.",
        )
    return text, ExtractionStatus.SUCCESS, None


def extract_candidate_name(text: str) -> str | None:
    """Best-effort guess at the candidate's name from the top of the resume."""
    for raw_line in text.splitlines()[:15]:
        line = raw_line.strip()
        if not line or EMAIL_RE.search(line) or any(ch.isdigit() for ch in line):
            continue
        if any(word in line.lower() for word in NAME_SKIP_WORDS):
            continue
        if NAME_LINE_RE.match(line):
            return line.title() if line.isupper() else line
    return None


def extract_candidate_email(text: str) -> str | None:
    """Return the first email address found in the resume text, if any."""
    match = EMAIL_RE.search(text)
    return match.group(0) if match else None
