"""Authentication blueprint: register, verify email, login (+ 2FA step), logout, password reset."""
from __future__ import annotations

import logging

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import login_required, login_user, logout_user

from models import User
from services import audit_service
from services.auth_service import (
    AuthError,
    authenticate,
    get_user_by_reset_token,
    register_user,
    request_password_reset,
    resend_verification,
    reset_password,
    verify_token,
)
from services.twofa_service import consume_recovery_code, verify_totp_code

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

    audit_service.log("register", "Account created", user=user, team_id=None)
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
    audit_service.log("email_verified", "Email verified", user=user)
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
    """
    Log an existing, verified user in.

    If the account has 2FA enabled, password success doesn't log them in yet —
    it stores a pending state in the session and sends them to /auth/two-factor.
    """
    if request.method == "GET":
        return render_template("auth/login.html")

    email = request.form.get("email", "")
    password = request.form.get("password", "")
    next_url = request.args.get("next")

    try:
        user = authenticate(email, password)
    except AuthError as exc:
        audit_service.log("login_failed", f"Failed login for {email}")
        flash(str(exc), "error")
        return render_template("auth/login.html", email=email), 400

    if user.totp_enabled:
        session["pending_2fa_user_id"] = user.id
        session["pending_2fa_next"] = next_url
        return redirect(url_for("auth.two_factor"))

    login_user(user)
    audit_service.log("login", "Logged in", user=user)
    flash("Welcome back!", "success")
    return redirect(next_url or url_for("dashboard.index"))


@auth_bp.route("/two-factor", methods=["GET", "POST"])
def two_factor():
    """Second step of login for accounts with 2FA enabled: TOTP code or a recovery code."""
    user_id = session.get("pending_2fa_user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = User.query.get(user_id)
    if not user:
        session.pop("pending_2fa_user_id", None)
        return redirect(url_for("auth.login"))

    if request.method == "GET":
        return render_template("auth/two_factor.html")

    code = (request.form.get("code") or "").strip()
    used_recovery = False

    if verify_totp_code(user.totp_secret, code):
        ok = True
    else:
        ok = consume_recovery_code(user, code)
        used_recovery = ok

    if not ok:
        audit_service.log("login_2fa_failed", "Failed 2FA code", user=user)
        flash("That code wasn't right. Try again.", "error")
        return render_template("auth/two_factor.html"), 400

    next_url = session.pop("pending_2fa_next", None)
    session.pop("pending_2fa_user_id", None)
    login_user(user)
    audit_service.log(
        "login", "Logged in via recovery code" if used_recovery else "Logged in with 2FA", user=user
    )
    if used_recovery:
        flash("Logged in with a recovery code. Consider regenerating your codes in Security settings.", "success")
    else:
        flash("Welcome back!", "success")
    return redirect(next_url or url_for("dashboard.index"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Request a password-reset email."""
    if request.method == "GET":
        return render_template("auth/forgot_password.html")

    request_password_reset(request.form.get("email", ""))
    flash("If that email is registered, a password reset link has been sent.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password_route(token: str):
    """Consume a password-reset link and set a new password."""
    if request.method == "GET":
        user = get_user_by_reset_token(token)
        if not user:
            flash("That reset link is invalid or has expired. Request a new one below.", "error")
            return redirect(url_for("auth.forgot_password"))
        return render_template("auth/reset_password.html", token=token)

    new_password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    try:
        user = reset_password(token, new_password, confirm_password)
    except AuthError as exc:
        flash(str(exc), "error")
        return render_template("auth/reset_password.html", token=token), 400

    audit_service.log("password_reset", "Password reset completed", user=user)
    flash("Your password has been reset. Log in with your new password.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/logout")
@login_required
def logout():
    from flask_login import current_user

    audit_service.log("logout", "Logged out", user=current_user)
    logout_user()
    flash("You've been logged out.", "success")
    return redirect(url_for("auth.login"))
