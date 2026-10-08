# ResumePilot — AI Resume Tailor

ResumePilot tailors **your actual uploaded resume** to a job description. It produces a complete, fact-checked DOCX and PDF that keep your original template. You decide which AI suggestions are applied. The ATS score is deterministic and explainable.

> Implementation status, decisions, known issues and requested changes live in **[progress.md](progress.md)**, the single source of truth for project progress.

## How it works

```
Upload resume (DOCX/PDF) ─► parse into a block model (source of truth, source claims, template fingerprint)
Paste/upload JD          ─► deterministic keyword extraction + Gemini analysis (validated against JD text)
Keyword evidence         ─► Supported / Partially supported / Missing (the JD is never evidence)
Suggestions              ─► Gemini rewrites + deterministic rules → fact-checked → shown individually
You Apply / Reject       ─► live projected ATS score
Generate                 ─► completeness check → write INTO your original DOCX → DOCX validation
                            → PDF (LibreOffice / MS Word) → PDF validation → DOCX/PDF consistency
                            → visual validation → page-count check (+ layout optimization) → identity check
                            → preview + downloads (only if every critical check passed)
Regenerate               ─► same resume + JD, accepted/rejected decisions preserved
```

### Key design points
- **Block model:** every paragraph of the uploaded resume is a block with a stable ID. Suggestions target blocks. The final resume is *all source blocks* plus the accepted changes, so nothing can be silently dropped.
- **Locked content:** the name, contact details, section headings, company/title/date lines, education and certifications are never edited.
- **Anti-fabrication** ([fact_check.py](backend/app/validation/fact_check.py)) rejects any suggestion that:
  - adds numbers, metrics, dates or years of experience;
  - adds technologies that aren't evidenced, or JD-only keywords;
  - adds new proper nouns;
  - adds skills, or drops skills or metrics.

  Blocked suggestions are listed in the UI.
- **Template preservation:** for DOCX uploads, the original file is reopened and only the text of changed paragraphs is replaced. A token diff maps text back onto the original runs, so bold labels, hyperlinks, tabs and italics survive. Styles, tables, images, profile photo, headers/footers, margins and numbering are untouched. Fingerprints of the original and generated files are compared, and so are the rendered page layouts.
- **PDF uploads:** a PDF has no editable template, so the layout is rebuilt from measured page size, margins, fonts, sizes, colours, spacing, bullets, right-aligned dates and the profile photo. Multi-column PDFs are linearised. This limitation is reported in the UI, and DOCX is recommended.

## ATS Compatibility Score (deterministic, [scoring.py](backend/app/ats/scoring.py))

| Category | Points | How |
|---|---|---|
| Keyword Match | 30 | Weighted JD keyword coverage (required ×2). Credit per keyword: exact 1, equivalent alias 0.75, related evidence 0.5. Repetition penalty. |
| Required Skills | 20 | Coverage of required skills |
| Experience Alignment | 15 | Dated years vs required, job-title similarity, seniority |
| Responsibilities Alignment | 15 | Token overlap of each JD responsibility with your bullets |
| Education / Certifications | 10 | Degree level vs requirement, requested certifications |
| Formatting / Parsing | 10 | Name, email, phone, standard headings, dated entries, bullets, length |

Original and tailored resumes are scored by the same function, which gives the before/after scores and coverage. Aliases (REST API ≈ RESTful, PostgreSQL ≈ Postgres, AWS ≈ Amazon Web Services) count as matches. Unrelated technologies (Django ≠ React, AWS ≠ Azure) never do.

## Requirements
- Python 3.11+ (developed on 3.13) and Node.js 20+
- A **DOCX→PDF converter**: LibreOffice (`soffice`, preferred) **or** Microsoft Word on Windows (used automatically via COM)
- Optional: **Tesseract OCR**, for scanned PDFs
- A **Gemini API key** for AI rewriting. Without one, the app still works with deterministic suggestions (skill ordering and exact terminology alignment) and shows a banner.

## Setup

```bash
# 1. Configuration
cp .env.example .env          # set GEMINI_API_KEY and GEMINI_MODEL

# 2. Backend
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # Windows  (Linux/macOS: .venv/bin/pip)
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev        # or: npm run build && npm start
```

Open http://localhost:3000. The frontend proxies `/api/*` to the backend (`BACKEND_URL`), so the Gemini key never reaches the browser. API docs: http://127.0.0.1:8000/api/docs

## Tests

```bash
cd backend
.venv/Scripts/python -m pytest -q
```

The 35 tests cover:
- upload validation;
- DOCX/PDF parsing;
- JD parsing;
- alias and negative matching;
- deterministic and explainable scoring, including the stuffing penalty;
- evidence rules;
- anti-fabrication;
- run-format preservation;
- completeness and identity checks;
- malformed, incomplete and failed AI responses;
- page-overflow optimization;
- full HTTP end-to-end flows for DOCX and PDF input.

The end-to-end flows cover upload → analyze → selective apply → generate → validate → preview → downloads → regenerate (both modes) → start over.

Tests use a fake AI provider ([tests/fake_ai.py](backend/tests/fake_ai.py)) that deliberately injects fabrications. Document tests are skipped if no converter is installed. Demo data lives only in [fixtures/](fixtures/) (`python fixtures/make_fixtures.py`) and is never used for real uploads. The identity check fails if demo names appear in output for a resume that doesn't contain them.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Gemini / converter / OCR availability |
| POST | `/api/resume/upload` | Upload resume → `session_id`, `job_id` (parse + render original + page count) |
| POST | `/api/jd/analyze` | Store JD (text or TXT/DOCX/PDF file) |
| POST | `/api/resume/analyze` | Job: JD analysis, structure, evidence, original ATS, suggestions |
| POST | `/api/resume/suggestions` | Current analysis + suggestions |
| POST | `/api/resume/apply-changes` | Apply/Reject decisions → projected score |
| POST | `/api/resume/score` | Deterministic score for current selections |
| POST | `/api/resume/tailor` | Job: generate with selections (full validation pipeline) |
| POST | `/api/resume/regenerate` | `mode`: `fresh` (new AI suggestions, keeps decisions) · `selections` · `suggestions` |
| POST | `/api/resume/validate` · `/api/resume/export` | Latest validation report / download ids |
| GET | `/api/jobs/{job_id}/status` | Real step-by-step status and progress |
| GET | `/api/download/{file_id}?s=…` | DOCX / PDF / ZIP (session-bound, unguessable ids) |
| GET | `/api/preview/{original\|tailored}/{page}?s=…` | Rendered page PNG |
| DELETE | `/api/sessions/{id}` | Start over: delete all files |

## Privacy
- Files are kept in a per-session temp directory under random names, and only addressed through unguessable IDs. Path traversal is blocked.
- Sessions expire after `SESSION_TTL_MINUTES` and are deleted on Start Over.
- Resume contents and API keys are never logged. Errors shown to users never include internals.
- Uploads are checked for extension, MIME type, file signature, size, integrity, macros and zip bombs.

## Troubleshooting
- **"PDF generation is unavailable"**: install LibreOffice or Microsoft Word. Set `LIBREOFFICE_PATH` if it isn't on PATH.
- **Scanned PDF rejected**: install Tesseract (and `tessdata`), or upload a DOCX.
- **Only deterministic suggestions**: set `GEMINI_API_KEY` in `.env` and restart the backend.
- **Page count grew**: the optimizer condenses changed paragraphs, then reduces paragraph spacing (never fonts). If the resume is still longer, the UI says so.
