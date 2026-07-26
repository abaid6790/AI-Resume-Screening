"""
Rule-based assistant: answers questions about how to use this application.

Deliberately keyword/pattern matching only — no LLM call, no external API,
zero cost, zero latency, and it structurally *cannot* talk about anything
other than the app, since every possible reply is one of the strings below.
"""
from __future__ import annotations

import re

# Each rule is (list of regex patterns, reply). Checked in order top to
# bottom; the first pattern that matches wins, so put specific rules before
# generic catch-alls (e.g. "score" rules before the generic "screen" rule).
_RULES: list[tuple[list[str], str]] = [
    (
        [r"upload.*resume", r"resume.*upload", r"drag.*drop"],
        "Go to Resumes → Upload Resumes. You can drag and drop multiple PDF "
        "resumes at once, or click to browse. Text is extracted automatically; "
        "a scanned PDF with no text layer is flagged \u201cNeeds OCR\u201d.",
    ),
    (
        [r"job description", r"\bjd\b", r"create.*job", r"post.*job"],
        "Go to Job Descriptions → New Job Description. Paste the text directly "
        "or upload a .txt/.pdf file. Relevant skills are detected automatically "
        "from the text.",
    ),
    (
        [r"how.*score", r"match score", r"what.*score mean", r"scoring"],
        "Match scores (0-100) come from Gemini comparing a resume to the job "
        "description. By default, 75+ is Shortlist, 50-74 is Review, and below "
        "50 is Reject — Gemini's own judgement can override that.",
    ),
    (
        [r"shortlist", r"recommendation", r"\breject\b", r"\breview\b"],
        "Recommendations are Shortlist, Review, or Reject. They're based on "
        "the match score and Gemini's assessment of the resume against the "
        "job description — see a candidate's report for the full explanation.",
    ),
    (
        [r"run.*screen", r"start.*screen", r"how.*screen"],
        "On the Screening page, pick a job description and the resumes to "
        "screen, then click \u201cRun AI screening\u201d. Each resume gets a "
        "score, matching/missing skills, and an explanation.",
    ),
    (
        [r"export", r"\bcsv\b", r"pdf report", r"download.*result"],
        "On a job's Results page, use the Export CSV or Export PDF buttons. "
        "They export exactly what's currently visible after your search/filter, "
        "not necessarily every result for that job.",
    ),
    (
        [r"filter", r"search"],
        "On the Results page you can search by candidate name and filter by "
        "score range or recommendation — it updates live, no page reload.",
    ),
    (
        [r"dark mode", r"light mode", r"\btheme\b"],
        "Click the sun/moon icon in the top-right of the navbar to toggle "
        "dark/light mode. Your preference is remembered on this device.",
    ),
    (
        [r"dashboard"],
        "The Dashboard shows total resumes, candidates screened, average "
        "match score, a score-distribution chart, and a recommendation "
        "breakdown, plus your most recent uploads.",
    ),
    (
        [r"privat", r"data safe", r"security", r"gdpr"],
        "Resumes and job descriptions are stored in this app's own database "
        "and file storage. Resume/job text is sent to Google's Gemini API "
        "only when you run AI screening.",
    ),
    (
        [r"file type", r"pdf only", r"what format", r"supported format"],
        "Resumes must be PDF. Job descriptions can be pasted as text or "
        "uploaded as .txt or .pdf.",
    ),
    (
        [r"verify", r"verification", r"confirm.*email"],
        "After registering, check your email for a verification link (valid "
        "24 hours). Didn't get it? Use \u201cResend verification email\u201d "
        "on the login page.",
    ),
    (
        [r"log ?in", r"sign ?in", r"\baccount\b", r"password"],
        "Use the Log in link in the top-right of the navbar. New here? "
        "Register first, then verify your email before logging in.",
    ),
    (
        [r"^(hi|hey|hello)\b"],
        "Hi! I'm the built-in assistant for the AI Resume Screening System. "
        "Ask me about uploading resumes, creating job descriptions, running "
        "AI screening, exporting results, or your account.",
    ),
    (
        [r"thank"],
        "You're welcome! Anything else about using this app I can help with?",
    ),
]

_FALLBACK = (
    "I can only help with questions about using this app \u2014 things like "
    "uploading resumes, creating job descriptions, running AI screening, "
    "exporting results, or your account. Could you rephrase around one of those?"
)


def get_reply(message: str) -> str:
    """Match a user message against known rules and return a canned reply."""
    if not message or not message.strip():
        return "Ask me something about using this app \u2014 uploads, screening, exports, your account, and so on."

    lowered = message.strip().lower()
    for patterns, reply in _RULES:
        for pattern in patterns:
            if re.search(pattern, lowered):
                return reply
    return _FALLBACK
