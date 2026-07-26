# Changelog

All notable changes to this project, in the order they were built.

## [1.1.0] — Accounts, Assistant & Design Pass

### Added
- Email/password registration with email verification (24h token expiry, dev-mode console fallback when no SMTP is configured)
- Login, logout, resend-verification flows via Flask-Login
- Global login gate — every route requires an authenticated, verified user except `/health`, `/auth/*`, and static files
- Demo account seeded by `flask seed-db` (`demo@resume-screening.local` / `DemoPass123`)
- Rule-based (non-LLM) in-app assistant — floating chat widget answering questions about using the app only
- Navbar user avatar/email + logout; login/signup CTAs when signed out
- Toast-style flash notifications, skip-to-content link, app-wide focus-visible states, loading spinners on long-running form submits, card entrance animations, dashboard stat-card icons

## [1.0.0] — Core Application (Phases 0–7)

### Phase 0 — Scaffolding
- Flask application factory, Blueprint structure, SQLite via SQLAlchemy, rotating file logging, error handlers, base Jinja2 layout with dark/light theme

### Phase 1 — Data Models
- `JobDescription`, `Resume`, `ScreeningResult` models with relationships and cascade deletes
- Seed script with realistic sample data

### Phase 2 — Job Description Management
- Paste-text or file-upload (`.txt`/`.pdf`) job description creation
- Keyword-based skill detection
- List / detail / delete views

### Phase 3 — Resume Upload & Extraction
- Drag-and-drop multi-file upload with real progress bar
- PDF text extraction (`pdfplumber`) with a distinct `Needs OCR` state for scanned PDFs
- Per-file success/failure reporting in a single batch

### Phase 4 — AI Screening Engine
- Gemini API integration with structured JSON output, schema validation, retry/backoff
- Score-threshold fallback when the model's own recommendation is missing/invalid
- Per-resume failure isolation — one bad call never kills a batch

### Phase 5 — Dashboard & Results UI
- Live dashboard stats and Chart.js visualizations (score distribution, recommendation breakdown), theme-aware
- Sortable, paginated results table

### Phase 6 — Search, Filter & Export
- Live client-side search (name), filter (score range, recommendation)
- CSV export (stdlib `csv`) and formatted PDF export (`reportlab`), both scoped to the currently filtered result set

### Phase 7 — UI/UX Hardening
- Accessibility pass (skip link, focus states, `prefers-reduced-motion` support)
- Responsive refinements, toast notifications, loading states on slow actions

### Fixed
- `sqlite3.OperationalError: unable to open database file` on Windows — relative `DATABASE_URL` values and platform path-separator handling now always resolve to an absolute path anchored to the project directory, independent of process working directory or launch method.
