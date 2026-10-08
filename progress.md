# AI Resume Tailor — Project Progress

## Current Status
- Overall completion: ~90% (all features implemented and verified; live Gemini run pending an API key)
- Current phase: Phase 22 — Final End-to-End Validation (done with fake AI + deterministic mode; live Gemini outstanding)
- Current task: Waiting for GEMINI_API_KEY to run the acceptance test with real Gemini and a real resume
- Last updated: 2026-10-07
- Application status: Runnable. Backend (FastAPI :8000) + frontend (Next.js :3000). 35/35 backend tests pass; frontend typecheck, lint and production build pass; full UI flow verified in headless Chrome (upload → review → generate → preview → download → regenerate).

## Completed
- [x] Phase 1 — Project setup (FastAPI backend, Next.js 16 + TS + Tailwind v4 frontend, .env.example, README)
- [x] Phase 2 — Frontend foundation (original design: off-white, charcoal, violet/pink/orange gradients; responsive)
- [x] Phase 3 — Resume upload & parsing (DOCX: body/tables/text boxes/headers/footers/styles/bullets/images; PDF: column-aware, bullets, styles, images; OCR fallback)
- [x] Phase 4 — JD processing (paste, TXT, DOCX, PDF; required/preferred/responsibilities/years/education/certs)
- [x] Phase 5 — Gemini integration (google-genai, backend only, retries, truncation detection, JSON validation)
- [x] Phase 6 — Resume analysis (keyword evidence Supported/Partial/Missing with explanations)
- [x] Phase 7 — Full resume tailoring (every editable block; final resume = all source blocks + accepted changes)
- [x] Phase 8 — User-controlled suggestions (per-change Apply/Reject, Apply All, Reject All, live projected score, ATS impact High/Medium/Low from real score delta)
- [x] Phase 9 — Anti-fabrication validation (numbers, metrics, dates, years, unsupported tech, JD-only keywords, new proper nouns, skill add/drop)
- [x] Phase 10 — Completeness validation (`resume_completeness_validator.py`)
- [x] Phase 11 — Deterministic ATS score (30/20/15/15/10/10)
- [x] Phase 12 — Explainable ATS + before/after coverage (expandable categories, matched/partial/missing, responsibilities, parsing checks)
- [x] Phase 13 — DOCX template preservation (edit original DOCX in place, run-level diff keeps formatting)
- [x] Phase 14 — Page count & layout preservation (rendered PDF page count; overflow → condense → spacing; never fonts)
- [x] Phase 15 — PDF generation (LibreOffice preferred; persistent MS Word COM worker fallback)
- [x] Phase 16 — DOCX/PDF content validation + consistency
- [x] Phase 17 — Visual validation (blank pages, out-of-bounds, overlaps, tiny text, orphan headings, sparse last page, missing photo/images, font substitution) + rendered layout similarity
- [x] Phase 18 — Preview (page images rendered from the exact downloadable PDF, page nav, original vs tailored compare) & downloads (DOCX/PDF/ZIP, secure session-bound file ids)
- [x] Phase 19 — One-click regeneration (fresh / with current selections / new suggestions only; decisions preserved; styles: balanced, ATS-focused, concise, achievement, conservative)
- [x] Phase 20 — Testing (35 pytest tests incl. HTTP E2E for DOCX and PDF input, page overflow)
- [x] Phase 21 — UI/UX refinement (desktop + mobile verified via screenshots)
- [x] Identity validation (name, employers, titles present; demo-data leak detection)
- [x] Session restore after page refresh; Start Over deletes all session files

## In Progress
- [ ] Phase 22 — Live acceptance test with real Gemini + a real user resume

## Pending
- [ ] Set GEMINI_API_KEY (and GEMINI_MODEL) in `.env`, then run the app with a real resume + JD and review AI suggestion quality
- [ ] Optional: install LibreOffice (preferred converter, also needed on Linux/macOS servers)
- [ ] Optional: install Tesseract for scanned-PDF OCR
- [ ] Optional: detect horizontal rules / decorative shapes in PDF uploads for the rebuild path

## Requested Changes
<!-- Add requested changes here as "- [ ] ..." items. Claude reads and implements them. -->

## Recently Completed Changes
- 2026-10-08: "Output is my original resume / only rearranged" — root cause: every Gemini call failed (503/504 overload on gemini-3.8-flash), so only deterministic skill reordering ran, with no visible warning. Fixes:
  - Model fallback chain (`GEMINI_FALLBACK_MODELS`, primary now gemini-3.5-flash; overloaded/429/404 models cool down 60s). Rewrite/repair tasks never use "lite" models and retry patiently (lite only made cosmetic edits).
  - `ai_status` (ok | weak | failed | disabled) in analysis + result payloads; red banners on Review (with "Retry AI tailoring") and Result when AI failed, made only minor edits, or nothing was applied.
  - Tailor prompt rewritten for real tailoring (summary always repositioned, JD-relevant bullets restructured in JD terminology, keep every fact, no filler, no invented seniority); temperature 0.5; weak responses retried.
  - Fact-check: blocks invented seniority ("Senior ..."), and dropping technologies/named items from the original paragraph (aliases like RESTful→REST APIs allowed).
  - Repair round: rejected AI rewrites are sent back once with the fact-checker's reasons and re-checked.
  - Fixed Gemini client race ("client has been closed") with a lock.
  - Tests: 38 pass (new: seniority/dropped facts, model fallback chain, repair round in e2e). Verified with real Gemini on the user's resume: 12 real rewrites, all validations pass.
- 2026-10-07: Fixed completeness check failing ('Candidate name present', 'Contact information present') for resumes whose name/contact header is an image (no text to detect, no OCR). The validator now only requires name/contact that were detected in the source text; the image is preserved by the template and checked by visual validation. Regression test `test_completeness_allows_name_contact_outside_text` added (36/36 pass). Verified on the real uploaded resume: all validations pass, 2 → 2 pages.
- 2026-10-07: Fixed 'Gemini API key is not configured': the key was saved after the backend started (restart required). Then the default model gemini-2.5-flash returned 404 (retired for new users) → switched to gemini-3.8-flash in .env, .env.example and config.py default.
- Built the complete frontend (upload, JD, real progress, review, result, preview, downloads, regenerate)
- Added `mode: "suggestions"` to `/api/resume/regenerate` (new suggestions without generating)
- Replaced per-conversion Word instances with one persistent COM worker (tests 32s → 10s, no RPC noise)
- Fixed alias rule producing "Backend developments" (rename only technology names)
- Fixed review sidebar overflow; step label consistency

## Files Created
- Root: `progress.md`, `README.md`, `.env.example`, `.gitignore`
- `fixtures/make_fixtures.py`, `fixtures/sample_resume.docx`, `fixtures/sample_jd.txt` (demo/test only)
- `backend/requirements.txt`
- `backend/app/main.py` — API routes
- `backend/app/core/` — `config.py`, `models.py`, `store.py`, `jobs.py`, `files.py`
- `backend/app/parsing/` — `sections.py`, `docx_xml.py`, `docx_parser.py`, `pdf_parser.py`, `resume_builder.py`
- `backend/app/ats/` — `lexicon.py`, `matching.py`, `jd_parser.py`, `evidence.py`, `scoring.py`
- `backend/app/ai/` — `base.py`, `gemini.py`, `prompts.py`, `service.py`
- `backend/app/tailoring/` — `rules.py`, `suggestions.py`, `pipeline.py`
- `backend/app/documents/` — `converter.py`, `docx_writer.py`, `pdf_rebuild.py`, `render.py`
- `backend/app/validation/` — `fact_check.py`, `resume_completeness_validator.py`, `content.py`, `visual.py`, `template.py`
- `backend/tests/` — `conftest.py`, `fake_ai.py`, `test_units.py`, `test_e2e.py`, `test_page_count.py`
- `frontend/src/lib/` — `api.ts`, `types.ts`, `diff.ts`
- `frontend/src/components/` — `TailorApp.tsx`, `UploadCard.tsx`, `JDCard.tsx`, `ProgressPanel.tsx`, `ReviewView.tsx`, `Suggestions.tsx`, `Ats.tsx`, `ResultView.tsx`, `ui.tsx`

## Files Modified
- `frontend/next.config.ts` (API rewrite proxy), `frontend/src/app/{layout.tsx,page.tsx,globals.css}`

## Backend Status
- FastAPI app with async job processing (thread pool) and real step status; per-session lock and busy guard (409).

## Frontend Status
- Next.js 16 App Router, client-side flow in `TailorApp.tsx`; `/api/*` proxied to the backend.

## Gemini Integration Status
- Implemented (`GeminiProvider`, google-genai). Key configured 2026-10-07; primary gemini-3.5-flash with fallback chain (GEMINI_FALLBACK_MODELS); 2.5-flash retired; lite models excluded from rewriting. Fake provider covers malformed, truncated and failed responses. Falls back to deterministic analysis/suggestions when unavailable.

## Resume Parsing Status
- DOCX verified on fixture (3 jobs, 2 projects, 1 education, 15 skills, photo, table, footer). PDF verified via Word-rendered PDF (same counts).

## Job Description Parsing Status
- Heuristic parser always runs; AI keywords are accepted only if they appear in the JD text.

## Resume Tailoring Status
- AI rewrites (per editable block) + deterministic skill reordering and technology-name alignment.

## Source Claim Tracking Status
- Deterministic claims (each skill + each editable paragraph) + AI claims whose quotes are verified verbatim. Suggestions carry claim IDs; unknown IDs are dropped.

## Anti-Fabrication Validation Status
- Active at suggestion time and again before generation. Verified by tests (Kubernetes, invented 50%, dropped 35%, "10 years", new company names all blocked).

## Resume Completeness Validation Status
- Active; generation stops if it fails.

## ATS Scoring Status
- Deterministic; same function scores original and tailored resumes.

## ATS Explainability Status
- Per-category explanation + matched/partial/missing + responsibilities + parsing checks in the UI.

## Before/After Coverage Status
- Keyword coverage %, exact matches before/after, required-skill coverage.

## Suggestion Review Status
- Done (statuses: suggested / accepted / rejected / applied).

## Regeneration Status
- Done (fresh / selections / suggestions-only); decisions preserved.

## DOCX Generation Status
- In-place edit of the original DOCX (DOCX input); layout rebuild (PDF input).

## PDF Generation Status
- Word COM (current machine) / LibreOffice (preferred when installed).

## Template Preservation Status
- Fixture: 100% (margins, fonts, sizes, colors, sections, tables, images, photo, footer, 99–100% rendered similarity). PDF input: rebuilt, limitation reported.

## Page Count Status
- From the rendered PDF (original DOCX is rendered too). Overflow optimization verified by a test.

## Visual Validation Status
- Implemented; critical issues block downloads.

## Content Validation Status
- DOCX, PDF, consistency and identity checks implemented; failures block downloads.

## Preview Status
- PNG pages from the final PDF; original vs tailored compare.

## Download Status
- DOCX / PDF / Both (ZIP); named `First_Last_Tailored_Resume.*`; old generations expire.

## Testing Status
- Backend: 35 passed. Frontend: tsc + eslint + `next build` clean; headless-Chrome UI run passed with no console errors.

## Known Issues
- Name/contact stored as an image (header banner) cannot be read without OCR → not detected; download filename falls back to Tailored_Resume and the ATS 'name detected' formatting point is lost. Installing Tesseract would allow detecting it.
- Gemini free-tier quota: heavy testing on 2026-10-08 hit 429 "exceeded your current quota" on gemini-3.5-flash and 3.8-flash; resets daily (or enable billing). Each tailoring uses ~4-6 calls. The backend must be restarted after any .env change.
- Repair round fixed 0 of 6 rejected rewrites on the user's real resume (2 of 4 on the sample) — not yet debugged live because the quota ran out; debug script idea: wrap ai.service.repair and print original/rejected/issues/repaired/recheck. The summary rewrite was among the blocked ones in that run.
- ATS score moves little (e.g. 74→75) when the resume already contains its supported JD keywords; missing keywords are intentionally never added.
- LibreOffice not installed → MS Word COM is used (Windows only). Linux/macOS deployments need LibreOffice.
- Tesseract not installed → scanned PDFs get a clear "please upload DOCX" message.
- PDF uploads: multi-column layouts are linearised and decorative shapes and rules are not reproduced (reported to the user in Template Preservation).
- Sessions are in-memory: a backend restart clears sessions (by design for privacy; a persistent store would be needed for multi-instance deployments).

## Decisions / Architecture Notes
- Block model: every source paragraph is a Block with a stable ID; the same DOCX paragraph enumeration is used for parsing and writing, so edits land in the exact original paragraph.
- Locked blocks (name, contact, headings, entry headers with company/title/dates, education, certifications, page headers/footers) are never edited.
- Gemini never sets numbers: the ATS score, coverage, impact and keyword support status are computed in Python.
- A JD keyword is "usable" only with exact/alias evidence, a defensible related term (e.g. sprints → Agile), or an AI quote verified verbatim in the resume.
- Priority on conflict: facts > completeness > template > readability > page count > ATS.
- New suggestions from a "fresh" one-click regenerate are auto-accepted (visible and reversible in "Adjust changes"); analysis-time suggestions are pre-selected but not applied until "Generate With My Selections".

## Next Recommended Step
- Once Gemini quota resets: debug why the repair round fails on the user's resume (see Known Issues), especially the blocked summary rewrite; then review suggestion quality in the UI.
