"""
Routes package.

Each module defines one Flask Blueprint. `register_blueprints` is called
once from the application factory so `app.py` doesn't need to know the
details of every route module.
"""
from __future__ import annotations

from flask import Flask


def register_blueprints(app: Flask) -> None:
    """Import and register every blueprint with the given Flask app."""
    from routes.dashboard import dashboard_bp
    from routes.jobs import jobs_bp
    from routes.resumes import resumes_bp
    from routes.screening import screening_bp
    from routes.export import export_bp
    from routes.auth import auth_bp
    from routes.assistant import assistant_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(jobs_bp, url_prefix="/jobs")
    app.register_blueprint(resumes_bp, url_prefix="/resumes")
    app.register_blueprint(screening_bp, url_prefix="/screening")
    app.register_blueprint(export_bp, url_prefix="/export")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(assistant_bp, url_prefix="/assistant")
