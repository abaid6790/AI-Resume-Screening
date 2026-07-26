"""Assistant blueprint: JSON endpoint backing the rule-based help widget."""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from services.assistant_service import get_reply

logger = logging.getLogger(__name__)

assistant_bp = Blueprint("assistant", __name__)


@assistant_bp.route("/ask", methods=["POST"])
def ask():
    """Return a canned, rule-based reply to a chat message about using this app."""
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", ""))[:500]  # defensive cap, not a real limit concern
    return jsonify({"reply": get_reply(message)})
