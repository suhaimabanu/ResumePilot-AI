"""AI Resume Tailor — FastAPI backend."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from .ai.service import get_provider
from .ats.jd_parser import parse_jd_text
from .ats.scoring import compare_scores, score_resume
from .core.config import settings
from .core.files import JD_TYPES, RESUME_TYPES, decode_text, sanitize_display_name, validate_upload
from .core.jobs import UserFacingError, jobs
from .core.store import Session, start_cleanup_thread, store
from .documents.converter import converter_status
from .parsing.resume_builder import extract_document_text
from .tailoring import pipeline
from .tailoring.suggestions import final_texts

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("api")

@asynccontextmanager
async def lifespan(_: FastAPI):
    start_cleanup_thread()
    yield


app = FastAPI(title="AI Resume Tailor API", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json",
              lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
                   allow_methods=["GET", "POST", "DELETE"], allow_headers=["*"])


@app.exception_handler(UserFacingError)
async def _user_error(_: Request, exc: UserFacingError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(RequestValidationError)
async def _validation_error(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": "Invalid request."})


@app.exception_handler(Exception)
async def _unhandled(_: Request, exc: Exception):
    log.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})


def _session(sid: str | None) -> Session:
    s = store.get(sid)
    if s is None:
        raise HTTPException(status_code=404, detail="Your session has expired. Please upload your resume again.")
    return s


def _busy_guard(session: Session) -> None:
    active = getattr(session, "active_job", None)
    if active:
        job = jobs.get(active)
        if job and job.status in ("queued", "processing"):
            raise HTTPException(status_code=409, detail="Another step is still running. Please wait for it to finish.")


def _submit(session: Session, kind: str, steps: list[str], fn, final_status: str = "completed"):
    _busy_guard(session)

    def run(ctx):
        with session.lock:
            return fn(ctx)

    job = jobs.submit(session.session_id, kind, steps, run, final_status=final_status)
    session.active_job = job.job_id  # type: ignore[attr-defined]
    return job


# ------------------------------------------------------------------------------------------------
@app.get("/api/health")
def health():
    provider = get_provider()
    return {
        "status": "ok",
        "gemini": {"configured": provider.available, "model": getattr(provider, "model", None)},
        "pdf_converter": converter_status(),
        "ocr": bool(settings.tesseract_path),
        "max_upload_mb": settings.max_upload_mb,
    }


@app.post("/api/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    data = await file.read(settings.max_upload_bytes + 1)
    ftype = validate_upload(file.filename or "", file.content_type, data, RESUME_TYPES)
    session = store.create()
    path = session.directory / f"resume_source.{ftype}"
    path.write_bytes(data)
    session.resume_path = path
    session.resume_filename = sanitize_display_name(file.filename or f"resume.{ftype}")
    job = _submit(session, "upload", pipeline.UPLOAD_STEPS, lambda ctx: pipeline.run_upload(session, ctx, ftype))
    return {"session_id": session.session_id, "job_id": job.job_id,
            "file": {"name": session.resume_filename, "type": ftype, "size": len(data)}}


@app.post("/api/jd/analyze")
async def analyze_jd(session_id: str = Form(...), jd_text: Optional[str] = Form(None),
                     file: Optional[UploadFile] = File(None)):
    session = _session(session_id)
    text = (jd_text or "").strip()
    source = "pasted"
    if file is not None and file.filename:
        data = await file.read(settings.max_upload_bytes + 1)
        ftype = validate_upload(file.filename, file.content_type, data, JD_TYPES)
        if ftype == "txt":
            text = decode_text(data)
        else:
            tmp = session.directory / f"jd_source.{ftype}"
            tmp.write_bytes(data)
            try:
                text = extract_document_text(tmp, ftype)
            except Exception as exc:
                raise UserFacingError("We couldn't read the job description file. Please paste the text instead.") from exc
            finally:
                tmp.unlink(missing_ok=True)
        source = sanitize_display_name(file.filename)
    text = text.strip()
    if len(text) < 80 or len(text.split()) < 15:
        raise UserFacingError("The job description is too short. Please paste the full job posting.")
    if len(text) > 60000:
        text = text[:60000]
    session.jd_text = text
    jd = parse_jd_text(text)
    return {"source": source, "characters": len(text), "words": len(text.split()),
            "job_title": jd.job_title, "keywords_preview": [k.term for k in jd.keywords][:25]}


class SessionBody(BaseModel):
    session_id: str
    style: Optional[Literal["balanced", "ats", "concise", "achievement", "conservative"]] = None


class DecisionsBody(BaseModel):
    session_id: str
    decisions: dict[str, Literal["accepted", "rejected", "suggested"]] = Field(default_factory=dict)


class RegenerateBody(BaseModel):
    session_id: str
    mode: Literal["fresh", "selections", "suggestions"] = "fresh"
    style: Optional[Literal["balanced", "ats", "concise", "achievement", "conservative"]] = None
    decisions: dict[str, Literal["accepted", "rejected", "suggested"]] = Field(default_factory=dict)


@app.post("/api/resume/analyze")
def analyze_resume(body: SessionBody):
    session = _session(body.session_id)
    if session.resume is None:
        raise UserFacingError("Your resume is still being read. Please wait a moment.")
    if not session.jd_text:
        raise UserFacingError("Please provide the job description first.")
    if body.style:
        session.style = body.style
    job = _submit(session, "analysis", pipeline.ANALYSIS_STEPS, lambda ctx: pipeline.run_analysis(session, ctx),
                  final_status="waiting_for_user")
    return {"job_id": job.job_id}


@app.post("/api/resume/suggestions")
def get_suggestions(body: SessionBody):
    session = _session(body.session_id)
    if session.jd_analysis is None:
        raise UserFacingError("Please analyze your resume first.")
    return pipeline.analysis_payload(session)


@app.post("/api/resume/apply-changes")
def apply_changes(body: DecisionsBody):
    """Record Apply/Reject decisions and return the deterministic projected ATS score."""
    session = _session(body.session_id)
    if session.resume is None or session.jd_analysis is None:
        raise UserFacingError("Please analyze your resume first.")
    _busy_guard(session)
    with session.lock:
        pipeline.apply_decisions(session, body.decisions)
        return _score_payload(session)


@app.post("/api/resume/score")
def score(body: DecisionsBody):
    session = _session(body.session_id)
    if session.resume is None or session.jd_analysis is None:
        raise UserFacingError("Please analyze your resume first.")
    return _score_payload(session)


def _score_payload(session: Session) -> dict:
    texts = final_texts(session.resume, session.changes)
    projected = score_resume(session.resume, session.jd_analysis, texts)
    original = session.original_ats or score_resume(session.resume, session.jd_analysis)
    return {"projected_ats": pipeline._public_score(projected), "comparison": compare_scores(original, projected),
            "changes": [c.model_dump() for c in session.changes]}


@app.post("/api/resume/tailor")
def tailor(body: DecisionsBody):
    """Generate the complete tailored resume with the user's selected changes."""
    session = _session(body.session_id)
    if session.jd_analysis is None:
        raise UserFacingError("Please analyze your resume first.")
    _busy_guard(session)
    pipeline.apply_decisions(session, body.decisions)
    job = _submit(session, "generation", pipeline.GENERATION_STEPS, lambda ctx: pipeline.run_generation(session, ctx))
    return {"job_id": job.job_id}


@app.post("/api/resume/regenerate")
def regenerate(body: RegenerateBody):
    """One-click regenerate: same resume + JD, keeps accepted/rejected decisions."""
    session = _session(body.session_id)
    if session.jd_analysis is None:
        raise UserFacingError("Please analyze your resume first.")
    _busy_guard(session)
    pipeline.apply_decisions(session, body.decisions)
    if body.style:
        session.style = body.style

    if body.mode == "suggestions":
        # New AI suggestions only (accepted/rejected decisions are kept); returns to review.
        job = _submit(session, "suggestions", ["generating_suggestions"],
                      lambda ctx: pipeline.run_suggestions_only(session, ctx), final_status="waiting_for_user")
        return {"job_id": job.job_id}
    if body.mode == "selections":
        fn = lambda ctx: pipeline.run_generation(session, ctx)  # noqa: E731
        steps = pipeline.GENERATION_STEPS
    else:
        def fn(ctx):
            ctx.step("generating_suggestions")
            pipeline._generate_suggestions(session, ctx, default_status="accepted")
            return pipeline.run_generation(session, ctx)
        steps = ["generating_suggestions"] + pipeline.GENERATION_STEPS
    job = _submit(session, "regeneration", steps, fn)
    return {"job_id": job.job_id}


@app.post("/api/resume/validate")
def validate(body: SessionBody):
    session = _session(body.session_id)
    if not session.result:
        raise UserFacingError("No tailored resume has been generated yet.")
    return {"validation": session.result["validation"], "template": session.result["template"],
            "pages": session.result["pages"]}


@app.post("/api/resume/export")
def export(body: SessionBody):
    session = _session(body.session_id)
    if not session.result:
        raise UserFacingError("No tailored resume has been generated yet.")
    return {"downloads": session.result["downloads"]}


@app.get("/api/sessions/{session_id}")
def session_state(session_id: str):
    session = _session(session_id)
    out = {"resume": pipeline.resume_summary(session) if session.resume else None,
           "has_jd": bool(session.jd_text), "analyzed": session.jd_analysis is not None,
           "result": session.result}
    if session.jd_analysis is not None:
        out["analysis"] = pipeline.analysis_payload(session)
    return out


@app.delete("/api/sessions/{session_id}")
def start_over(session_id: str):
    """Start Over: permanently delete the uploaded resume, JD and generated files."""
    session = _session(session_id)
    _busy_guard(session)
    store.delete(session.session_id)
    return {"deleted": True}


@app.get("/api/jobs/{job_id}/status")
def job_status(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job.")
    data = job.to_dict()
    if job.status == "completed" and job.result and "downloads" in job.result:
        d = job.result["downloads"]
        data["docx_url"] = f"/api/download/{d['docx']['file_id']}?s={job.session_id}"
        data["pdf_url"] = f"/api/download/{d['pdf']['file_id']}?s={job.session_id}"
        data["ats_score"] = job.result["ats_score"]
        data["page_count"] = job.result["page_count"]
    return data


@app.get("/api/download/{file_id}")
def download(file_id: str, s: str = Query(..., min_length=10)):
    session = _session(s)
    stored = session.files.get(file_id)
    if stored is None or not stored.path.exists():
        raise HTTPException(status_code=404, detail="This download has expired. Please regenerate your resume.")
    # Defence against path traversal: the file must live inside the session directory.
    if session.directory.resolve() not in stored.path.resolve().parents:
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(stored.path, media_type=stored.media_type, filename=stored.download_name,
                        headers={"Cache-Control": "no-store"})


@app.get("/api/preview/{which}/{page}")
def preview(which: Literal["original", "tailored"], page: int, s: str = Query(..., min_length=10),
            g: Optional[int] = None):
    session = _session(s)
    if page < 1 or page > 50:
        raise HTTPException(status_code=404, detail="Page not found.")
    if which == "original":
        prefix = "original"
    else:
        if not session.result:
            raise HTTPException(status_code=404, detail="No preview available yet.")
        prefix = f"g{session.result['generation']}"
    path = session.directory / "preview" / f"{prefix}_p{page}.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Page not found.")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "private, max-age=600"})
