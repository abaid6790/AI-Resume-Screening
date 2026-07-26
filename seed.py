"""
Sample data for manual testing of the Phase 1 schema, before uploads (Phase 3)
and AI screening (Phase 4) exist. Run via `flask seed-db` (see app.py).
"""
from __future__ import annotations

import datetime as dt

from models import ExtractionStatus, JobDescription, RecommendationEnum, Resume, ScreeningResult, User, db


def seed_database() -> None:
    """Wipe and repopulate all tables with a small, realistic sample dataset."""
    ScreeningResult.query.delete()
    Resume.query.delete()
    JobDescription.query.delete()
    db.session.commit()

    demo_user = User.query.filter_by(email="demo@resume-screening.local").first()
    if not demo_user:
        demo_user = User(email="demo@resume-screening.local", is_verified=True)
        demo_user.set_password("DemoPass123")
        db.session.add(demo_user)
        db.session.commit()

    job = JobDescription(
        title="Senior Backend Engineer (Python)",
        raw_text=(
            "We are looking for a Senior Backend Engineer with 5+ years of "
            "experience in Python, Flask or Django, PostgreSQL, and REST API "
            "design. Experience with Docker, CI/CD, and AWS is a strong plus. "
            "Bachelor's degree in Computer Science or equivalent experience required."
        ),
        parsed_skills=["Python", "Flask", "Django", "PostgreSQL", "REST APIs", "Docker", "AWS", "CI/CD"],
        source_filename=None,
    )
    db.session.add(job)
    db.session.flush()  # assigns job.id without committing yet

    resumes = [
        Resume(
            filename="asha_kapoor_resume.pdf",
            filepath="uploads/asha_kapoor_resume.pdf",
            candidate_name="Asha Kapoor",
            candidate_email="asha.kapoor@example.com",
            raw_text="Senior Software Engineer with 6 years in Python, Flask, PostgreSQL, AWS...",
            extraction_status=ExtractionStatus.SUCCESS,
            uploaded_at=dt.datetime.utcnow(),
        ),
        Resume(
            filename="daniel_osei_resume.pdf",
            filepath="uploads/daniel_osei_resume.pdf",
            candidate_name="Daniel Osei",
            candidate_email="daniel.osei@example.com",
            raw_text="Backend developer, 2 years experience with Node.js and MongoDB...",
            extraction_status=ExtractionStatus.SUCCESS,
            uploaded_at=dt.datetime.utcnow(),
        ),
        Resume(
            filename="mei_lin_resume.pdf",
            filepath="uploads/mei_lin_resume.pdf",
            candidate_name="Mei Lin",
            candidate_email="mei.lin@example.com",
            raw_text=None,
            extraction_status=ExtractionStatus.NEEDS_OCR,
            extraction_error="Scanned PDF with no embedded text layer.",
            uploaded_at=dt.datetime.utcnow(),
        ),
    ]
    db.session.add_all(resumes)
    db.session.flush()

    results = [
        ScreeningResult(
            resume_id=resumes[0].id,
            job_description_id=job.id,
            match_score=88,
            extracted_skills=["Python", "Flask", "PostgreSQL", "AWS", "Docker"],
            extracted_education=[{"degree": "B.Sc. Computer Science", "institution": "Example University"}],
            extracted_experience=[{"title": "Senior Software Engineer", "years": 6, "company": "Example Corp"}],
            matching_skills=["Python", "Flask", "PostgreSQL", "AWS"],
            missing_skills=["CI/CD"],
            explanation="Strong alignment with required stack and seniority level.",
            recommendation=RecommendationEnum.SHORTLIST,
        ),
        ScreeningResult(
            resume_id=resumes[1].id,
            job_description_id=job.id,
            match_score=41,
            extracted_skills=["Node.js", "MongoDB", "JavaScript"],
            extracted_education=[{"degree": "B.Sc. Information Technology", "institution": "Example College"}],
            extracted_experience=[{"title": "Backend Developer", "years": 2, "company": "Example Startup"}],
            matching_skills=["REST APIs"],
            missing_skills=["Python", "Flask", "PostgreSQL", "AWS", "Docker"],
            explanation="Core tech stack does not match; experience level is below the target seniority.",
            recommendation=RecommendationEnum.REJECT,
        ),
        ScreeningResult(
            resume_id=resumes[2].id,
            job_description_id=job.id,
            match_score=None,
            recommendation=RecommendationEnum.PENDING,
            explanation="Awaiting OCR/text extraction before this resume can be screened.",
        ),
    ]
    db.session.add_all(results)
    db.session.commit()
