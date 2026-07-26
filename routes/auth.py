"""Authentication blueprint: register, verify email, login, logout."""
from __future__ import annotations

import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from services.auth_service import (
    AuthError,
    authenticate,
    register_user,
    resend_verification,
    verify_token,
)

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Create an account (unverified) and send a verification email."""
    if request.method == "GET":
        return render_template("auth/register.html")

    email = request.form.get("email", "")
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    try:
        user = register_user(email, password, confirm_password)
    except AuthError as exc:
        flash(str(exc), "error")
        return render_template("auth/register.html", email=email), 400

    return redirect(url_for("auth.check_email", email=user.email))


@auth_bp.route("/check-email")
def check_email():
    """Landing page telling the person to check their inbox after registering."""
    return render_template("auth/check_email.html", email=request.args.get("email", ""))


@auth_bp.route("/verify/<token>")
def verify_email(token: str):
    """Consume a verification link, activate the account, and log the person in."""
    user = verify_token(token)
    if not user:
        flash("That verification link is invalid or has expired. Request a new one below.", "error")
        return redirect(url_for("auth.resend"))

    login_user(user)
    flash("Email verified — welcome!", "success")
    return redirect(url_for("dashboard.index"))


@auth_bp.route("/resend", methods=["GET", "POST"])
def resend():
    """Request a fresh verification link."""
    if request.method == "GET":
        return render_template("auth/resend.html")

    resend_verification(request.form.get("email", ""))
    # Same message regardless of whether the email exists/is already verified,
    # so this endpoint can't be used to enumerate registered accounts.
    flash("If that email is registered and unverified, a new link has been sent.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Log an existing, verified user in."""
    if request.method == "GET":
        return render_template("auth/login.html")

    email = request.form.get("email", "")
    password = request.form.get("password", "")

    try:
        user = authenticate(email, password)
    except AuthError as exc:
        flash(str(exc), "error")
        return render_template("auth/login.html", email=email), 400

    login_user(user)
    flash("Welcome back!", "success")
    next_url = request.args.get("next")
    return redirect(next_url or url_for("dashboard.index"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You've been logged out.", "success")
    return redirect(url_for("auth.login"))
