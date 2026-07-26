"""Registration/login helpers: validation, verification tokens, and email dispatch."""
from __future__ import annotations

import datetime as dt
import logging
import secrets

from flask import url_for

from models import User, db
from services.email_service import send_email

logger = logging.getLogger(__name__)

VERIFICATION_TOKEN_TTL_HOURS = 24


class AuthError(Exception):
    """Raised for user-facing registration/login validation errors."""


def register_user(email: str, password: str, confirm_password: str) -> User:
    """Create an unverified user and send them a verification email. Raises AuthError on bad input."""
    email = (email or "").strip().lower()
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise AuthError("Enter a valid email address.")
    if len(password) < 8:
        raise AuthError("Password must be at least 8 characters.")
    if password != confirm_password:
        raise AuthError("Passwords do not match.")
    if User.query.filter_by(email=email).first():
        raise AuthError("An account with that email already exists.")

    user = User(email=email)
    user.set_password(password)
    _issue_verification_token(user)
    db.session.add(user)
    db.session.commit()

    send_verification_email(user)
    logger.info("Registered new user: %s", email)
    return user


def _issue_verification_token(user: User) -> None:
    user.verification_token = secrets.token_urlsafe(32)
    user.verification_sent_at = dt.datetime.utcnow()


def send_verification_email(user: User) -> None:
    verify_url = url_for("auth.verify_email", token=user.verification_token, _external=True)
    body = (
        "Welcome to the AI Resume Screening System!\n\n"
        f"Please verify your email by visiting this link (valid for "
        f"{VERIFICATION_TOKEN_TTL_HOURS} hours):\n{verify_url}\n\n"
        "If you didn't create this account, you can safely ignore this email."
    )
    send_email(user.email, "Verify your email", body)


def resend_verification(email: str) -> None:
    """
    Regenerate and resend a verification token.

    Silently no-ops if the email is unknown or already verified — the caller
    always shows the same generic message either way, to avoid leaking
    which emails have accounts.
    """
    user = User.query.filter_by(email=(email or "").strip().lower()).first()
    if not user or user.is_verified:
        return
    _issue_verification_token(user)
    db.session.commit()
    send_verification_email(user)


def is_token_expired(user: User) -> bool:
    if not user.verification_sent_at:
        return True
    return dt.datetime.utcnow() - user.verification_sent_at > dt.timedelta(hours=VERIFICATION_TOKEN_TTL_HOURS)


def verify_token(token: str) -> User | None:
    """Mark the matching user verified and return them, or None if the token is invalid/expired."""
    user = User.query.filter_by(verification_token=token).first()
    if not user or is_token_expired(user):
        return None
    user.is_verified = True
    user.verification_token = None
    db.session.commit()
    logger.info("Verified user: %s", user.email)
    return user


def authenticate(email: str, password: str) -> User:
    """Return the user if credentials are valid and verified. Raises AuthError otherwise."""
    user = User.query.filter_by(email=(email or "").strip().lower()).first()
    if not user or not user.check_password(password):
        raise AuthError("Invalid email or password.")
    if not user.is_verified:
        raise AuthError("Please verify your email before logging in.")
    return user
