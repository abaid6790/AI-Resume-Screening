"""Account blueprint: security settings — 2FA and password change."""
from __future__ import annotations

import logging

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from models import db
from services import audit_service
from services.auth_service import AuthError, change_password
from services.twofa_service import (
    generate_recovery_codes,
    generate_secret,
    get_provisioning_uri,
    hash_recovery_codes,
    render_qr_svg,
    verify_totp_code,
)

logger = logging.getLogger(__name__)

account_bp = Blueprint("account", __name__)


@account_bp.route("/security")
@login_required
def security():
    """Security settings landing page: 2FA status + change password form."""
    return render_template("account/security.html")


@account_bp.route("/security/2fa/setup", methods=["GET", "POST"])
@login_required
def two_factor_setup():
    """Start 2FA setup: show a QR code, then confirm with one real code before enabling."""
    if current_user.totp_enabled:
        flash("Two-factor authentication is already enabled.", "error")
        return redirect(url_for("account.security"))

    if request.method == "GET":
        # A fresh secret is generated each time this page loads and held in the
        # session (not saved to the user) until they prove they can generate a
        # matching code — so a half-finished setup never silently enables 2FA.
        secret = generate_secret()
        session["pending_totp_secret"] = secret
        uri = get_provisioning_uri(secret, current_user.email)
        qr_svg = render_qr_svg(uri)
        return render_template("account/two_factor_setup.html", secret=secret, qr_svg=qr_svg)

    secret = session.get("pending_totp_secret")
    code = (request.form.get("code") or "").strip()

    if not secret or not verify_totp_code(secret, code):
        flash("That code didn't match. Scan the QR code again and try the current 6-digit code.", "error")
        uri = get_provisioning_uri(secret or generate_secret(), current_user.email)
        return render_template(
            "account/two_factor_setup.html", secret=secret, qr_svg=render_qr_svg(uri)
        ), 400

    recovery_codes = generate_recovery_codes()
    current_user.totp_secret = secret
    current_user.totp_enabled = True
    current_user.totp_recovery_codes = hash_recovery_codes(recovery_codes)
    db.session.commit()
    session.pop("pending_totp_secret", None)

    audit_service.log("2fa_enabled", "Two-factor authentication enabled", user=current_user)
    return render_template("account/two_factor_recovery_codes.html", recovery_codes=recovery_codes)


@account_bp.route("/security/2fa/disable", methods=["POST"])
@login_required
def two_factor_disable():
    """Disable 2FA — requires the current password as confirmation."""
    password = request.form.get("password", "")
    if not current_user.check_password(password):
        flash("Incorrect password.", "error")
        return redirect(url_for("account.security"))

    current_user.totp_enabled = False
    current_user.totp_secret = None
    current_user.totp_recovery_codes = []
    db.session.commit()

    audit_service.log("2fa_disabled", "Two-factor authentication disabled", user=current_user)
    flash("Two-factor authentication has been disabled.", "success")
    return redirect(url_for("account.security"))


@account_bp.route("/security/change-password", methods=["POST"])
@login_required
def change_password_route():
    """Change password while logged in (requires the current password)."""
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_new_password", "")

    try:
        change_password(current_user, current_password, new_password, confirm_password)
    except AuthError as exc:
        flash(str(exc), "error")
        return redirect(url_for("account.security"))

    audit_service.log("password_changed", "Password changed", user=current_user)
    flash("Password changed.", "success")
    return redirect(url_for("account.security"))
