"""
AI Resume Screening System — application entry point.

Uses the Flask application-factory pattern so the app can be configured
differently for development, testing, and production without code changes.
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user

from config import get_config
from models import db
from routes import register_blueprints


def configure_logging(app: Flask) -> None:
    """Attach a rotating file handler + console handler to the app logger."""
    log_folder = app.config["LOG_FOLDER"]
    log_folder.mkdir(parents=True, exist_ok=True)

    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO"), logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    file_handler = RotatingFileHandler(
        log_folder / "app.log", maxBytes=1_000_000, backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    app.logger.setLevel(log_level)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)

    # Keep Werkzeug's own request logs at the same level rather than default noise
    logging.getLogger("werkzeug").setLevel(log_level)


def register_error_handlers(app: Flask) -> None:
    """Register friendly error pages for common HTTP errors."""

    @app.errorhandler(404)
    def not_found(error: Exception):  # noqa: ANN001, ANN202
        app.logger.warning("404 Not Found: %s", error)
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error: Exception):  # noqa: ANN001, ANN202
        app.logger.exception("500 Internal Server Error: %s", error)
        return render_template("errors/500.html"), 500

    @app.errorhandler(413)
    def file_too_large(error: Exception):  # noqa: ANN001, ANN202
        app.logger.warning("413 Payload Too Large: %s", error)
        return render_template("errors/500.html", message="Upload is too large."), 413


def ensure_runtime_folders(app: Flask) -> None:
    """Create upload/report/database/log folders if they don't already exist."""
    for folder_key in ("UPLOAD_FOLDER", "REPORTS_FOLDER", "LOG_FOLDER"):
        app.config[folder_key].mkdir(parents=True, exist_ok=True)

    # config.py guarantees this is an absolute sqlite:/// URI (or non-sqlite,
    # e.g. Postgres, which we leave alone since there's no local file/folder).
    db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    prefix = "sqlite:///"
    if db_uri.startswith(prefix) and not db_uri[len(prefix):].startswith(":memory:"):
        db_file = Path(db_uri[len(prefix):])
        db_file.parent.mkdir(parents=True, exist_ok=True)


def create_app(config_name: str | None = None) -> Flask:
    """Application factory: builds and configures the Flask app instance."""
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    ensure_runtime_folders(app)
    configure_logging(app)
    app.logger.info("Using database: %s", app.config["SQLALCHEMY_DATABASE_URI"])

    db.init_app(app)
    with app.app_context():
        db.create_all()  # Phase 0/1: simple create-all; revisit with Alembic later

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to continue."
    login_manager.login_message_category = "error"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        from models import User

        return db.session.get(User, int(user_id))

    register_blueprints(app)
    register_error_handlers(app)

    _PUBLIC_ENDPOINTS = {"dashboard.health", "static"}

    @app.before_request
    def require_login():
        """Gate every route behind login except auth pages, /health, and static files."""
        endpoint = request.endpoint
        if endpoint is None:
            return
        if endpoint in _PUBLIC_ENDPOINTS or endpoint.startswith("auth."):
            return
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))

    if not app.config.get("GEMINI_API_KEY"):
        app.logger.warning(
            "GEMINI_API_KEY is not set. AI screening (Phase 4) will fail until it is "
            "configured in your .env file."
        )

    @app.context_processor
    def inject_globals() -> dict[str, str]:
        """Make app-wide template variables available without passing them each time."""
        return {"app_name": "AI Resume Screening System"}

    @app.cli.command("seed-db")
    def seed_db_command() -> None:
        """Wipe and repopulate the database with sample data (`flask seed-db`)."""
        from seed import seed_database

        seed_database()
        app.logger.info("Database seeded with sample data")
        print("Database seeded with sample data.")
        print("Demo login: demo@resume-screening.local / DemoPass123")

    app.logger.info("AI Resume Screening System started (config=%s)", config_name or "default")
    return app


app = create_app(os.environ.get("FLASK_ENV"))


if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", False), host="0.0.0.0", port=5000)
