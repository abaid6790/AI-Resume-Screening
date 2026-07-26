"""
Job description ingestion helpers.

Extracts raw text from an uploaded .txt/.pdf file and pulls out a plain
keyword-based skills list. This is intentionally zero-cost/zero-API — Phase 4
adds a Gemini pass for structured extraction from resumes and can reuse or
upgrade this same skills list for job descriptions.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class JDServiceError(Exception):
    """Raised for any recoverable error while ingesting a job description."""


# Curated, case-insensitive keyword list covering common languages, frameworks,
# data/ML tools, databases, cloud/DevOps, and a few soft skills.
SKILL_KEYWORDS: list[str] = [
    # Languages
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust",
    "Ruby", "PHP", "Swift", "Kotlin", "Scala", "SQL",
    # Web frameworks
    "Flask", "Django", "FastAPI", "React", "Angular", "Vue", "Node.js",
    "Express", "Spring", "Spring Boot", ".NET",
    # Data / ML
    "Pandas", "NumPy", "TensorFlow", "PyTorch", "Scikit-learn", "Machine Learning",
    "Deep Learning", "NLP", "Data Science", "Data Analysis",
    # Databases
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "Oracle", "Elasticsearch",
    # Cloud / DevOps
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "CI/CD", "Terraform",
    "Jenkins", "Git", "GitHub Actions", "Linux",
    # APIs / architecture
    "REST APIs", "GraphQL", "Microservices", "gRPC",
    # Soft / general
    "Agile", "Scrum", "Communication", "Leadership", "Project Management",
]


def extract_text_from_upload(filepath: Path, extension: str) -> str:
    """Read raw text out of an uploaded job description file (.txt or .pdf)."""
    extension = extension.lower().lstrip(".")
    if extension == "txt":
        return Path(filepath).read_text(encoding="utf-8", errors="ignore")
    if extension == "pdf":
        return _extract_pdf_text(filepath)
    raise JDServiceError(f'Unsupported file type ".{extension}".')


def _extract_pdf_text(filepath: Path) -> str:
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise JDServiceError("PDF support is not installed on the server.") from exc

    text_parts: list[str] = []
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
    except Exception as exc:  # noqa: BLE001 - surface as a clean, user-facing error
        logger.warning("Failed to extract text from PDF %s: %s", filepath, exc)
        raise JDServiceError(f"Could not read the PDF file: {exc}") from exc

    return "\n".join(text_parts)


def extract_skills(text: str) -> list[str]:
    """Return the subset of SKILL_KEYWORDS that appear in `text` (case-insensitive)."""
    if not text:
        return []
    lowered = text.lower()
    return [skill for skill in SKILL_KEYWORDS if skill.lower() in lowered]
