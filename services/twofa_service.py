"""
Two-factor authentication (TOTP) helpers.

Uses pyotp for the actual TOTP math (RFC 6238 — same algorithm Google
Authenticator / Authy use) and qrcode's SVG image factory so the setup QR
code can be embedded directly inline in the page with zero image files and
no Pillow dependency.
"""
from __future__ import annotations

import io
import logging
import secrets

import pyotp
import qrcode
import qrcode.image.svg
from werkzeug.security import check_password_hash, generate_password_hash

from models import User, db

logger = logging.getLogger(__name__)

RECOVERY_CODE_COUNT = 8


def generate_secret() -> str:
    """A new random base32 TOTP secret."""
    return pyotp.random_base32()


def get_provisioning_uri(secret: str, email: str, issuer: str = "AI Resume Screening") -> str:
    """The otpauth:// URI an authenticator app scans/imports."""
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def render_qr_svg(data: str) -> str:
    """Render a QR code for `data` as an inline SVG string (no file, no Pillow)."""
    factory = qrcode.image.svg.SvgImage
    img = qrcode.make(data, image_factory=factory, box_size=8)
    buffer = io.BytesIO()
    img.save(buffer)
    return buffer.getvalue().decode("utf-8")


def verify_totp_code(secret: str, code: str) -> bool:
    """Check a 6-digit code, allowing a little clock drift (±1 time step)."""
    if not secret or not code:
        return False
    try:
        return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)
    except Exception:  # noqa: BLE001 - any malformed input just means "not valid"
        return False


def generate_recovery_codes(count: int = RECOVERY_CODE_COUNT) -> list[str]:
    """Plaintext recovery codes — shown to the user exactly once, never stored as-is."""
    return [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(count)]


def hash_recovery_codes(codes: list[str]) -> list[str]:
    return [generate_password_hash(code) for code in codes]


def consume_recovery_code(user: User, code: str) -> bool:
    """
    Check `code` against the user's stored (hashed) recovery codes. If it
    matches, remove it (single-use) and persist. Returns whether it matched.
    """
    if not user.totp_recovery_codes or not code:
        return False

    code = code.strip()
    for hashed in user.totp_recovery_codes:
        if check_password_hash(hashed, code):
            remaining = [h for h in user.totp_recovery_codes if h != hashed]
            user.totp_recovery_codes = remaining
            db.session.commit()
            logger.info("Recovery code consumed for user %s (%d remaining)", user.email, len(remaining))
            return True
    return False
