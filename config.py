"""
Application configuration.

Config is environment-driven (via .env / real env vars) so the same
codebase runs unmodified in development, testing, and production.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def _resolve_sqlite_uri(raw_uri: str, base_dir: Path) -> str:
    """
    Make a sqlite:// URI absolute and forward-slashed, regardless of the
    process's current working directory.

    A relative sqlite path (e.g. "sqlite:///database/app.db") only works if
    the app happens to be launched with that exact folder as CWD. Any other
    launch method (IDE debugger, double-click, a different shell, a Windows
    scheduled task) resolves it somewhere else entirely and sqlite raises
    "unable to open database file" because the target folder doesn't exist
    there. Resolving against BASE_DIR removes that dependency completely.
    """
    prefix = "sqlite:///"
    if not raw_uri.startswith(prefix) or raw_uri[len(prefix):].startswith(":memory:"):
        return raw_uri  # not sqlite, or an in-memory DB — nothing to resolve

    path = Path(raw_uri[len(prefix):])
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return f"{prefix}{path.as_posix()}"


_DEFAULT_DATABASE_URL = f"sqlite:///{(BASE_DIR / 'database' / 'app.db').as_posix()}"


class Config:
    """Base configuration shared by all environments."""

    # --- Core Flask ---
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    JSON_SORT_KEYS: bool = False

    # --- Database ---
    SQLALCHEMY_DATABASE_URI: str = _resolve_sqlite_uri(
        os.environ.get("DATABASE_URL", _DEFAULT_DATABASE_URL), BASE_DIR
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # --- File storage ---
    UPLOAD_FOLDER: Path = BASE_DIR / "uploads"
    REPORTS_FOLDER: Path = BASE_DIR / "reports"
    ALLOWED_RESUME_EXTENSIONS: set[str] = {"pdf"}
    ALLOWED_JD_EXTENSIONS: set[str] = {"pdf", "txt"}
    MAX_CONTENT_LENGTH: int = 20 * 1024 * 1024  # 20 MB total request size cap

    # --- Gemini API ---
    GEMINI_API_KEY: str | None = os.environ.get("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    GEMINI_MAX_RETRIES: int = int(os.environ.get("GEMINI_MAX_RETRIES", "3"))
    GEMINI_TIMEOUT_SECONDS: int = int(os.environ.get("GEMINI_TIMEOUT_SECONDS", "60"))

    # --- Logging ---
    LOG_FOLDER: Path = BASE_DIR / "logs"
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

    # --- Screening thresholds ---
    SHORTLIST_THRESHOLD: int = 75
    REVIEW_THRESHOLD: int = 50

    # --- Email (account verification) ---
    # If MAIL_SERVER is left unset, emails are logged instead of sent, so
    # registration/verification works out of the box without real SMTP
    # credentials. Set these in .env to send real email.
    MAIL_SERVER: str | None = os.environ.get("MAIL_SERVER") or None
    MAIL_PORT: int = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS: bool = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME: str | None = os.environ.get("MAIL_USERNAME") or None
    MAIL_PASSWORD: str | None = os.environ.get("MAIL_PASSWORD") or None
    MAIL_DEFAULT_SENDER: str = os.environ.get("MAIL_DEFAULT_SENDER", "no-reply@resume-screening.local")


class DevelopmentConfig(Config):
    DEBUG: bool = True
    SQLALCHEMY_ECHO: bool = False


class ProductionConfig(Config):
    DEBUG: bool = False

    def __init__(self) -> None:
        if self.SECRET_KEY == "dev-secret-key-change-me":
            raise RuntimeError(
                "Refusing to start in production with the default SECRET_KEY. "
                "Set SECRET_KEY in your environment."
            )


class TestingConfig(Config):
    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"
    WTF_CSRF_ENABLED: bool = False


CONFIG_MAP: dict[str, type[Config]] = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}


def get_config(name: str | None = None) -> type[Config]:
    """Resolve a config class by environment name (falls back to FLASK_ENV)."""
    key = name or os.environ.get("FLASK_ENV", "default")
    return CONFIG_MAP.get(key, DevelopmentConfig)
