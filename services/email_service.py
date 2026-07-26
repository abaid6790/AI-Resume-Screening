"""
Email sending, with a safe local-dev fallback.

If MAIL_SERVER is not configured, the email is logged instead of sent, so
registration/verification works out of the box in development without real
SMTP credentials. Configure MAIL_* in .env to send real email.
"""
from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

from flask import current_app

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> None:
    """Send a plain-text email, or log it if no mail server is configured."""
    mail_server = current_app.config.get("MAIL_SERVER")
    if not mail_server:
        logger.warning(
            "MAIL_SERVER not configured — logging email instead of sending.\n"
            "----- EMAIL (dev mode) -----\nTo: %s\nSubject: %s\n\n%s\n-----------------------------",
            to, subject, body,
        )
        return

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = current_app.config.get("MAIL_DEFAULT_SENDER", "no-reply@resume-screening.local")
    message["To"] = to

    port = current_app.config.get("MAIL_PORT", 587)
    username = current_app.config.get("MAIL_USERNAME")
    password = current_app.config.get("MAIL_PASSWORD")
    use_tls = current_app.config.get("MAIL_USE_TLS", True)

    try:
        with smtplib.SMTP(mail_server, port, timeout=10) as server:
            if use_tls:
                server.starttls()
            if username and password:
                server.login(username, password)
            server.sendmail(message["From"], [to], message.as_string())
        logger.info("Sent email to %s: %s", to, subject)
    except Exception as exc:  # noqa: BLE001 - surfaced to the caller, logged here for diagnostics
        logger.error("Failed to send email to %s: %s", to, exc)
        raise
