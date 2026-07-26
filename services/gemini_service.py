"""
Gemini API integration for AI resume screening.

Kept isolated from routes/models/scoring logic so it can be unit tested with
a mocked model response (`_call_model` is the one function that touches the
network) instead of making real API calls on every test run.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from flask import current_app

logger = logging.getLogger(__name__)

REQUIRED_KEYS = {
    "extracted_skills",
    "extracted_education",
    "extracted_experience",
    "matching_skills",
    "missing_skills",
    "match_score",
    "explanation",
    "recommendation",
}

ALLOWED_RECOMMENDATIONS = {"Shortlist", "Review", "Reject"}

PROMPT_TEMPLATE = """You are an expert technical recruiter. Compare the RESUME to the JOB DESCRIPTION and respond with ONLY a single JSON object — no markdown formatting, no code fences, no commentary before or after it.

JOB DESCRIPTION:
\"\"\"
{job_description}
\"\"\"

RESUME:
\"\"\"
{resume_text}
\"\"\"

Return exactly this JSON shape:
{{
  "candidate_name": string or null,
  "extracted_skills": [string, ...],
  "extracted_education": [{{"degree": string, "institution": string}}, ...],
  "extracted_experience": [{{"title": string, "company": string, "years": number}}, ...],
  "matching_skills": [string, ...],
  "missing_skills": [string, ...],
  "match_score": integer from 0 to 100,
  "explanation": string, 2-4 sentences explaining the score,
  "recommendation": one of "Shortlist", "Review", "Reject"
}}

Scoring guidance:
- 75-100 -> Shortlist: strong alignment with required skills, experience level, and education.
- 50-74 -> Review: partial alignment; some important requirements are missing.
- 0-49 -> Reject: weak alignment with the role's core requirements.

Respond with ONLY the JSON object.
"""


class GeminiServiceError(Exception):
    """Raised when the Gemini API cannot produce a usable screening result."""


def screen_resume_with_gemini(resume_text: str, job_description_text: str) -> dict[str, Any]:
    """
    Call Gemini (with retries) to screen a resume against a job description.

    Returns a validated dict matching the documented JSON shape. Raises
    GeminiServiceError if the API key is missing, every retry is exhausted,
    or the model never returns valid, schema-conformant JSON.
    """
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        raise GeminiServiceError(
            "GEMINI_API_KEY is not configured. Set it in your .env file to enable AI screening."
        )

    model_name = current_app.config.get("GEMINI_MODEL", "gemini-2.0-flash")
    max_retries = current_app.config.get("GEMINI_MAX_RETRIES", 3)
    timeout_seconds = current_app.config.get("GEMINI_TIMEOUT_SECONDS", 60)

    prompt = PROMPT_TEMPLATE.format(
        job_description=job_description_text.strip(),
        resume_text=(resume_text or "").strip() or "(No text could be extracted from this resume.)",
    )

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            raw_text = _call_model(api_key, model_name, prompt, timeout_seconds)
            return _parse_and_validate(raw_text)
        except Exception as exc:  # noqa: BLE001 - any failure here is retried, then wrapped
            last_error = exc
            logger.warning("Gemini screening attempt %s/%s failed: %s", attempt, max_retries, exc)
            if attempt < max_retries:
                time.sleep(min(2**attempt, 10))

    raise GeminiServiceError(f"Gemini screening failed after {max_retries} attempts: {last_error}")


def _call_model(api_key: str, model_name: str, prompt: str, timeout_seconds: int) -> str:
    """Make the actual API call. Isolated so it's the only thing tests need to mock."""
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"},
        request_options={"timeout": timeout_seconds},
    )
    text = getattr(response, "text", None)
    if not text:
        raise GeminiServiceError("Gemini returned an empty response.")
    return text


def _parse_and_validate(raw_text: str) -> dict[str, Any]:
    """Parse Gemini's response as JSON and validate/clamp it against the expected schema."""
    cleaned = _strip_code_fences(raw_text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise GeminiServiceError(f"Gemini response was not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise GeminiServiceError("Gemini response JSON was not an object.")

    missing_keys = REQUIRED_KEYS - data.keys()
    if missing_keys:
        raise GeminiServiceError(f"Gemini response missing required keys: {sorted(missing_keys)}")

    # Defensive clamping/typing rather than trusting the model completely.
    try:
        data["match_score"] = max(0, min(100, int(data.get("match_score"))))
    except (TypeError, ValueError):
        data["match_score"] = None

    if data.get("recommendation") not in ALLOWED_RECOMMENDATIONS:
        data["recommendation"] = None  # scoring_service falls back to threshold-based logic

    for list_key in ("extracted_skills", "extracted_education", "extracted_experience",
                      "matching_skills", "missing_skills"):
        if not isinstance(data.get(list_key), list):
            data[list_key] = []

    if not isinstance(data.get("explanation"), str):
        data["explanation"] = None

    if not isinstance(data.get("candidate_name"), str):
        data["candidate_name"] = None

    return data


def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers some models add even when told not to."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
    return stripped.strip()
