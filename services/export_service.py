"""
Export screening results to CSV and PDF.

CSV uses the stdlib csv module (no extra dependency). PDF uses reportlab.
Both operate on whatever subset of results is passed in, so the caller
(routes/export.py) controls whether that's "all results" or a filtered set.
"""
from __future__ import annotations

import csv
import datetime as dt
import logging
import uuid
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from flask import current_app

from models import JobDescription, ScreeningResult

logger = logging.getLogger(__name__)

CSV_HEADERS = [
    "Candidate", "Email", "Match Score", "Recommendation",
    "Matching Skills", "Missing Skills", "Years of Experience", "Screened At",
]


def _years_of_experience(result: ScreeningResult) -> float:
    years = 0.0
    for exp in result.extracted_experience or []:
        try:
            years += float(exp.get("years") or 0)
        except (TypeError, ValueError, AttributeError):
            continue
    return years


def _reports_folder() -> Path:
    folder = Path(current_app.config["REPORTS_FOLDER"])
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _safe_slug(text: str) -> str:
    """Turn a job title into a filesystem-safe filename fragment."""
    slug = "".join(ch if ch.isalnum() else "_" for ch in text)[:50].strip("_")
    return slug or "export"


def export_results_csv(job: JobDescription, results: list[ScreeningResult]) -> Path:
    """Write a CSV of the given results and return its path."""
    folder = _reports_folder()
    filepath = folder / f"{_safe_slug(job.title)}_results_{uuid.uuid4().hex[:8]}.csv"

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)
        for result in results:
            years = _years_of_experience(result)
            writer.writerow([
                result.resume.candidate_name or result.resume.filename,
                result.resume.candidate_email or "",
                result.match_score if result.match_score is not None else "",
                result.recommendation.value,
                "; ".join(result.matching_skills or []),
                "; ".join(result.missing_skills or []),
                f"{years:.1f}" if years else "",
                result.created_at.strftime("%Y-%m-%d %H:%M"),
            ])

    logger.info("Exported CSV: %s (%d rows)", filepath, len(results))
    return filepath


def export_results_pdf(job: JobDescription, results: list[ScreeningResult]) -> Path:
    """Write a formatted PDF summary of the given results and return its path."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    folder = _reports_folder()
    filepath = folder / f"{_safe_slug(job.title)}_results_{uuid.uuid4().hex[:8]}.pdf"

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(
        str(filepath), pagesize=landscape(letter),
        topMargin=0.5 * inch, bottomMargin=0.5 * inch,
        leftMargin=0.5 * inch, rightMargin=0.5 * inch,
    )

    generated_at = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    elements = [
        Paragraph(f"Screening Results: {xml_escape(job.title)}", styles["Title"]),
        Paragraph(f"{len(results)} candidate(s) \u00b7 generated {generated_at}", styles["Normal"]),
        Spacer(1, 0.25 * inch),
    ]

    table_data = [["Candidate", "Score", "Recommendation", "Matching Skills", "Missing Skills"]]
    for result in results:
        table_data.append([
            result.resume.candidate_name or result.resume.filename,
            str(result.match_score) if result.match_score is not None else "\u2014",
            result.recommendation.value,
            ", ".join(result.matching_skills or []) or "\u2014",
            ", ".join(result.missing_skills or []) or "\u2014",
        ])

    table = Table(
        table_data, repeatRows=1,
        colWidths=[1.7 * inch, 0.7 * inch, 1.1 * inch, 3.1 * inch, 3.1 * inch],
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F6659")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E1D8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FBFAF7")]),
    ]))
    elements.append(table)

    doc.build(elements)
    logger.info("Exported PDF: %s (%d rows)", filepath, len(results))
    return filepath
