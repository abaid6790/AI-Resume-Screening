# Roadmap / Upgrade Ideas

This is the honest list of what's *not* built yet — organized by what matters most first. Nothing here is required; the app is fully usable as-is. Pick whatever fits your actual use case.

## 🎯 Recommended first (if you deploy this beyond just yourself)

1. **CSRF protection** (`Flask-WTF`) — no form on this app currently has CSRF tokens.
2. **Rate limiting** on `/auth/login` and `/auth/register` (`Flask-Limiter`) — no brute-force protection yet.
3. **Alembic migrations** — replace `db.create_all()` before you change the schema on a database that already has real data in it.

---

## 🔐 Security & Accounts

- [ ] CSRF protection on all forms
- [ ] Rate limiting / login lockout after repeated failures
- [ ] "Forgot password" flow (currently only initial email verification exists)
- [ ] Optional 2FA (TOTP)
- [ ] Multi-user teams with roles (Admin / Recruiter / Viewer) — today, any verified user sees *all* data; there's no per-user or per-team data isolation
- [ ] Audit log (who screened what, who deleted what)
- [ ] Session timeout / "remember me" control

## 🧪 Quality & Operations

- [ ] Automated test suite (`pytest`) covering models, services, and routes
- [ ] CI pipeline (GitHub Actions): lint (`ruff`), type-check (`mypy`), run tests on every PR
- [ ] Alembic migrations
- [ ] Dockerfile + `docker-compose.yml` (app + Postgres) for one-command local/prod setup
- [ ] Structured logging / error tracking (e.g. Sentry) for production
- [ ] Health check expanded to verify DB connectivity, not just process liveness

## 🤖 AI & Screening

- [ ] Background job queue (Celery or RQ) so large upload batches don't block the request/response cycle
- [ ] OCR fallback (e.g. Tesseract) for scanned PDFs currently flagged "Needs OCR"
- [ ] Configurable scoring weights per job description (e.g. weight "years of experience" vs "skill match" differently)
- [ ] Support for additional LLM providers as a fallback/comparison (OpenAI, Claude, local models)
- [ ] Prompt versioning + A/B testing to measure scoring consistency over time
- [ ] Bulk re-screen (re-run all resumes for a job against an updated job description)
- [ ] Duplicate/near-duplicate resume detection

## 📊 Product Features

- [ ] Candidate notes/comments and tags (recruiter collaboration)
- [ ] Saved filter views ("my shortlist", "needs review this week")
- [ ] Email notifications when a screening batch finishes
- [ ] Candidate self-upload portal (a public link candidates use to submit directly)
- [ ] Interview scheduling integration (Calendly-style or calendar API)
- [ ] Analytics dashboard across all jobs (time-to-shortlist, average scores by role, funnel drop-off)
- [ ] Multi-language resume support

## 🎨 UI/UX

- [ ] Guided onboarding tour for first-time users
- [ ] Keyboard shortcuts for power users (e.g. `j`/`k` to move through results)
- [ ] More chart types on the dashboard (trends over time, per-job comparisons)
- [ ] PWA / installable mobile experience
- [ ] Full accessibility audit (axe-core) beyond the manual pass already done
- [ ] White-label / custom branding support

## ☁️ Infrastructure

- [ ] Production deployment guide (gunicorn + nginx, or Docker Compose)
- [ ] S3-compatible object storage for uploaded files (instead of local disk)
- [ ] Caching layer (Redis) for dashboard aggregate queries at scale
- [ ] CDN for static assets

---

**Already production-friendly today:** `DATABASE_URL` swaps to Postgres/MySQL with no code changes, `gunicorn` is already in `requirements.txt`, and the config system is fully environment-driven (dev/prod/testing).
