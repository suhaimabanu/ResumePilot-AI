"""End-to-end workflows executed as background jobs (upload, analysis/suggestions, generation)."""
from __future__ import annotations

import logging
import re
import shutil
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import docx as python_docx

from ..ai import service as ai
from ..ats.evidence import assess_keywords
from ..ats.jd_parser import parse_jd_text
from ..ats.scoring import compare_scores, score_resume
from ..core.jobs import JobContext, UserFacingError
from ..core.models import Change
from ..core.store import Session
from ..documents.converter import converter_name, docx_to_pdf
from ..documents.docx_writer import docx_text, write_tailored_docx
from ..documents.pdf_rebuild import build_docx_from_blocks
from ..documents.render import layout_similarity, page_signature, render_pages
from ..parsing.docx_parser import docx_fingerprint
from ..parsing.pdf_parser import pdf_fingerprint, pdf_page_count, pdf_text
from ..parsing.resume_builder import parse_resume
from ..validation.content import validate_consistency, validate_document_text, validate_identity
from ..validation.fact_check import check_change
from ..validation.resume_completeness_validator import validate_completeness
from ..validation.template import compare_templates
from ..validation.visual import validate_visual
from .rules import rule_suggestions
from .suggestions import build_changes, final_texts

log = logging.getLogger("pipeline")

UPLOAD_STEPS = ["parsing_resume", "rendering_original"]
ANALYSIS_STEPS = ["parsing_jd", "analyzing", "generating_suggestions"]
GENERATION_STEPS = ["applying_changes", "fact_checking", "completeness", "scoring", "generating_docx",
                    "validating_docx", "generating_pdf", "validating_pdf", "visual_validation", "page_count",
                    "final_validation"]


# ------------------------------------------------------------------------------------------------
# Upload
# ------------------------------------------------------------------------------------------------
def run_upload(session: Session, ctx: JobContext, file_type: str) -> dict[str, Any]:
    ctx.step("parsing_resume")
    resume = parse_resume(session.resume_path, file_type, session.resume_filename)

    ctx.step("rendering_original")
    page_count_source = "pdf"
    if file_type == "pdf":
        session.original_pdf_path = session.resume_path
        resume.page_count = pdf_page_count(session.resume_path)
    elif converter_name():
        pdf, _ = docx_to_pdf(session.resume_path, session.directory / "original")
        session.original_pdf_path = pdf
        resume.page_count = pdf_page_count(pdf)
    else:
        page_count_source = "docx_metadata"
        ctx.note("Page count estimated from document metadata (no PDF renderer available).")
    resume.fingerprint.page_count = resume.page_count
    if session.original_pdf_path:
        render_pages(session.original_pdf_path, session.directory / "preview", "original")
    session.resume = resume
    return {"resume": resume_summary(session), "page_count_source": page_count_source}


def resume_summary(session: Session) -> dict[str, Any]:
    r = session.resume
    assert r is not None
    return {
        "filename": r.filename,
        "file_type": r.file_type,
        "page_count": r.page_count,
        "counts": r.summary_counts(),
        "name": r.name,
        "headline": r.headline,
        "sections": [{"key": s.key, "title": s.title} for s in r.sections],
        "experience": [{"title": e.title, "organization": e.organization, "dates": e.dates,
                        "bullets": len(e.bullet_block_ids)} for e in r.experience],
        "skills": r.skills,
        "certifications": r.certifications,
        "warnings": r.warnings,
        "ocr_used": r.ocr_used,
        "profile_photo": r.fingerprint.profile_photo,
        "template": {"tables": r.fingerprint.tables, "images": r.fingerprint.images,
                     "fonts": r.fingerprint.fonts[:5], "page_size": r.fingerprint.page_size},
        "structuring": r.structuring,
        "original_preview_pages": _count_pages(session, "original"),
    }


def _count_pages(session: Session, prefix: str) -> int:
    d = session.directory / "preview"
    return len(list(d.glob(f"{prefix}_p*.png"))) if d.exists() else 0


# ------------------------------------------------------------------------------------------------
# Analysis + suggestions
# ------------------------------------------------------------------------------------------------
def run_analysis(session: Session, ctx: JobContext) -> dict[str, Any]:
    resume = session.resume
    if resume is None or not session.jd_text:
        raise UserFacingError("Please upload a resume and provide a job description first.")
    ctx.step("parsing_jd")
    heuristic = parse_jd_text(session.jd_text)
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_struct = pool.submit(ai.refine_structure, resume)
        f_jd = pool.submit(ai.analyze_jd, session.jd_text, resume, heuristic)
        struct_notes = f_struct.result()
        jd, ai_evidence, jd_notes = f_jd.result()
    for n in struct_notes + jd_notes:
        ctx.note(n)
    if not jd.keywords:
        raise UserFacingError("We couldn't find any skills or requirements in the job description. "
                              "Please paste the full job posting.")
    session.jd_analysis = jd

    ctx.step("analyzing")
    session.keyword_evidence = assess_keywords(jd, resume.full_text, ai_evidence)
    session.original_ats = score_resume(resume, jd)

    ctx.step("generating_suggestions")
    session.changes = []
    _generate_suggestions(session, ctx)
    return analysis_payload(session)


def _generate_suggestions(session: Session, ctx: JobContext, default_status: str = "suggested") -> None:
    resume, jd = session.resume, session.jd_analysis
    assert resume is not None and jd is not None
    kept = [c for c in session.changes if c.status in ("accepted", "applied", "rejected")]
    locked = {c.block_id for c in kept}
    ai_props, notes = ai.tailor(resume, jd, session.keyword_evidence, locked, session.style)
    for n in notes:
        ctx.note(n)
    if not ai.get_provider().available:
        session.ai_status = "disabled"
    elif not ai_props:
        session.ai_status = "failed"
    else:
        # "weak": the AI answered but left most prose untouched — the user must not mistake it for a tailoring.
        prose = {b.id: b.text for b in resume.blocks
                 if b.editable and b.text.strip() and b.role != "skills" and b.id not in locked}
        rewritten = sum(1 for p in ai_props if p["id"] in prose and
                        re.sub(r"\s+", " ", p["text"]).strip() != re.sub(r"\s+", " ", prose[p["id"]]).strip())
        session.ai_status = "weak" if prose and rewritten < max(1, 0.3 * len(prose)) else "ok"
    rules = rule_suggestions(resume, jd, session.keyword_evidence, locked)
    next_idx = max([int(c.change_id[3:]) for c in session.changes] + [0]) + 1
    base = final_texts(resume, kept)
    new_changes, blocked = build_changes(resume, jd, session.keyword_evidence, ai_props, rules, next_idx, base)
    # One repair round: send rejected AI rewrites back with the fact-checker's reasons, then re-check them.
    covered = {c.block_id for c in new_changes}
    to_repair = list({b["block_id"]: b for b in blocked if b["block_id"] not in covered}.values())
    if to_repair and session.ai_status in ("ok", "weak"):
        repaired = ai.repair(to_repair, resume, jd)
        if repaired:
            idx = max([int(c.change_id[3:]) for c in new_changes] + [next_idx - 1]) + 1
            fixed, still_blocked = build_changes(resume, jd, session.keyword_evidence, repaired, [], idx, base)
            new_changes += fixed
            fixed_ids = {c.block_id for c in fixed}
            blocked = [b for b in blocked if b["block_id"] not in fixed_ids and b["block_id"] not in
                       {s["block_id"] for s in still_blocked}] + still_blocked
            log.info("repair: %d of %d rejected rewrites fixed", len(fixed), len(to_repair))
    for c in new_changes:
        c.status = default_status  # type: ignore[assignment]
    for c in kept:
        c.pinned = c.status in ("accepted", "applied")
    session.changes = sorted(kept + new_changes, key=lambda c: _block_order(session, c.block_id))
    session.blocked = blocked  # type: ignore[attr-defined]
    if blocked:
        ctx.note(f"{len(blocked)} AI suggestion(s) were blocked by fact-checking and not shown.")


def _block_order(session: Session, block_id: str) -> int:
    return next((i for i, b in enumerate(session.resume.blocks) if b.id == block_id), 0)


def run_suggestions_only(session: Session, ctx: JobContext) -> dict[str, Any]:
    ctx.step("generating_suggestions")
    _generate_suggestions(session, ctx)
    return analysis_payload(session)


def analysis_payload(session: Session) -> dict[str, Any]:
    resume, jd = session.resume, session.jd_analysis
    assert resume is not None and jd is not None
    projected = score_resume(resume, jd, final_texts(resume, session.changes))
    evidence = [e.model_dump() for e in session.keyword_evidence]
    return {
        "jd": {
            "job_title": jd.job_title, "company": jd.company, "years_experience": jd.years_experience,
            "required_skills": jd.required_skills, "preferred_skills": jd.preferred_skills,
            "responsibilities": jd.responsibilities, "education_requirements": jd.education_requirements,
            "certifications": jd.certifications, "soft_skills": jd.soft_skills,
            "keywords": [k.model_dump() for k in jd.keywords], "source": jd.source,
        },
        "keyword_evidence": evidence,
        "keyword_groups": {
            "supported": [e for e in evidence if e["status"] == "supported"],
            "partial": [e for e in evidence if e["status"] == "partial"],
            "missing": [e for e in evidence if e["status"] == "missing"],
        },
        "original_ats": _public_score(session.original_ats),
        "projected_ats": _public_score(projected),
        "changes": [c.model_dump() for c in session.changes],
        "blocked_count": len(getattr(session, "blocked", []) or []),
        "blocked": getattr(session, "blocked", [])[:20],
        "claims": [c.model_dump() for c in resume.claims[:200]],
        "resume": resume_summary(session),
        "ai_enabled": ai.get_provider().available,
        "ai_status": session.ai_status,
    }


def _public_score(score: dict | None) -> dict | None:
    if score is None:
        return None
    return {k: v for k, v in score.items() if k != "keywords"} | {
        "keywords": [{k: r[k] for k in ("term", "importance", "status", "match_type", "count")} for r in score["keywords"]]
    }


def apply_decisions(session: Session, decisions: dict[str, str]) -> None:
    by_id = {c.change_id: c for c in session.changes}
    for cid, status in decisions.items():
        c = by_id.get(cid)
        if c is None or status not in ("accepted", "rejected", "suggested"):
            continue
        c.status = status  # type: ignore[assignment]
        c.pinned = status == "accepted"


# ------------------------------------------------------------------------------------------------
# Generation
# ------------------------------------------------------------------------------------------------
def _download_base(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9]+", "_", name or "").strip("_")
    return f"{safe}_Tailored_Resume" if safe and len(safe) <= 60 else "Tailored_Resume"


def run_generation(session: Session, ctx: JobContext) -> dict[str, Any]:
    resume, jd = session.resume, session.jd_analysis
    if resume is None or jd is None:
        raise UserFacingError("Please analyze your resume against a job description first.")

    ctx.step("applying_changes")
    selected = [c for c in session.changes if c.status in ("accepted", "applied")]

    ctx.step("fact_checking")
    source_text = resume.full_text
    for c in selected:
        block = resume.block(c.block_id)
        v = check_change(block, c.suggested, source_text, session.keyword_evidence)
        if not v.passed:  # defence in depth — should never happen for validated suggestions
            c.status, c.validation = "rejected", v
            ctx.note(f"{c.change_id} failed the final fact check and was not applied.")
    selected = [c for c in session.changes if c.status in ("accepted", "applied")]
    texts = final_texts(resume, session.changes)
    fact_report = {"passed": True, "checked": len(selected),
                   "detail": f"{len(selected)} applied change(s) verified against your original resume"}

    ctx.step("completeness")
    completeness = validate_completeness(resume, texts)
    if not completeness["passed"]:
        failed = [c["check"] for c in completeness["checks"] if not c["passed"]]
        log.error("completeness failed: %s", failed)
        raise UserFacingError("The tailored resume failed the completeness check, so it was not exported. "
                              "Please try Regenerate.")

    ctx.step("scoring")
    tailored_ats = score_resume(resume, jd, texts)
    original_ats = session.original_ats or score_resume(resume, jd)

    session.generation += 1
    gen = session.generation
    out_dir = session.directory / f"gen{gen}"
    out_dir.mkdir(parents=True, exist_ok=True)
    base_name = _download_base(resume.name)
    target_pages = resume.page_count
    attempts = [{"spacing": 1.0, "collapse": False, "condense": False},
                {"spacing": 1.0, "collapse": False, "condense": True},
                {"spacing": 0.85, "collapse": True, "condense": True},
                {"spacing": 0.7, "collapse": True, "condense": True}]
    optimization_log: list[str] = []
    condensed_done = False
    result_docs: dict[str, Any] = {}
    for n, attempt in enumerate(attempts):
        if attempt["condense"] and not condensed_done:
            condensed_done = True
            changed = _condense_changes(session, texts, ctx)
            if changed:
                optimization_log.append(f"Condensed {changed} tailored paragraph(s) to their original length.")
                texts = final_texts(resume, session.changes)
                tailored_ats = score_resume(resume, jd, texts)
            elif attempt["spacing"] == 1.0:
                continue
        docx_path = out_dir / f"{base_name}.docx"
        result_docs = _build_and_validate(session, ctx, texts, docx_path, out_dir, attempt)
        pages = result_docs["pdf_pages"]
        if target_pages is None or pages <= target_pages or n == len(attempts) - 1:
            break
        optimization_log.append(f"Attempt {n + 1}: {pages} pages vs {target_pages} original — optimizing layout.")
        ctx.note(f"Page overflow detected ({pages} vs {target_pages}); optimizing layout.")

    if not result_docs["docx_validation"]["passed"] or not result_docs["pdf_validation"]["passed"]:
        raise UserFacingError("The generated documents failed content validation, so downloads were not enabled. "
                              "Please try Regenerate.")
    if not result_docs["visual"]["passed"]:
        raise UserFacingError("The generated document has layout problems (" +
                              "; ".join(i["message"] for i in result_docs["visual"]["issues"] if i["severity"] == "critical")[:300] +
                              "). Downloads were not enabled.")

    ctx.step("final_validation")
    pdf_path: Path = result_docs["pdf_path"]
    docx_path = result_docs["docx_path"]
    identity = validate_identity(resume, texts, result_docs["pdf_text"])
    if not identity["passed"]:
        raise UserFacingError("The generated resume did not match your uploaded resume's identity, so it was not "
                              "exported. Please try again.")
    sim = None
    if session.original_pdf_path:
        sim = layout_similarity(page_signature(session.original_pdf_path), page_signature(pdf_path))
    template = compare_templates(resume.fingerprint, result_docs["fingerprint"], sim,
                                 rebuilt=resume.file_type == "pdf", visual=result_docs["visual"])
    preview_pages = render_pages(pdf_path, session.directory / "preview", f"g{gen}")
    pages = result_docs["pdf_pages"]
    page_report = {
        "original": target_pages,
        "tailored": pages,
        "preserved": target_pages is None or pages == target_pages,
        "status": ("preserved" if target_pages is None or pages == target_pages else
                   ("shorter" if pages < target_pages else "longer")),
        "optimization": optimization_log,
        "source": "rendered PDF",
    }
    if page_report["status"] == "longer":
        ctx.note("The tailored resume is longer than the original even after layout optimization "
                 "(fonts were not shrunk to protect readability).")

    zip_path = out_dir / f"{base_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(docx_path, docx_path.name)
        zf.write(pdf_path, pdf_path.name)
    session.drop_files({"tailored_docx", "tailored_pdf", "bundle_zip"})
    f_docx = session.register_file(docx_path, "tailored_docx", docx_path.name,
                                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    f_pdf = session.register_file(pdf_path, "tailored_pdf", pdf_path.name, "application/pdf")
    f_zip = session.register_file(zip_path, "bundle_zip", zip_path.name, "application/zip")
    for c in session.changes:
        if c.status == "accepted":
            c.status = "applied"
    _cleanup_old_generations(session, keep=gen)

    validation = {
        "facts": fact_report,
        "completeness": completeness,
        "docx": result_docs["docx_validation"],
        "pdf": result_docs["pdf_validation"],
        "consistency": result_docs["consistency"],
        "visual": result_docs["visual"],
        "identity": identity,
        "page_count": page_report,
    }
    validation["summary"] = {
        "Facts": fact_report["passed"], "Completeness": completeness["passed"],
        "DOCX": result_docs["docx_validation"]["passed"], "PDF": result_docs["pdf_validation"]["passed"],
        "Consistency": result_docs["consistency"]["passed"], "Visual": result_docs["visual"]["passed"],
        "Identity": identity["passed"],
    }
    result = {
        "status": "completed",
        "generation": gen,
        "ats": {"original": _public_score(original_ats), "tailored": _public_score(tailored_ats),
                "comparison": compare_scores(original_ats, tailored_ats)},
        "ats_score": tailored_ats["total"],
        "page_count": pages,
        "pages": page_report,
        "template": template,
        "validation": validation,
        "downloads": {
            "docx": {"file_id": f_docx.file_id, "name": f_docx.download_name},
            "pdf": {"file_id": f_pdf.file_id, "name": f_pdf.download_name},
            "both": {"file_id": f_zip.file_id, "name": f_zip.download_name},
        },
        "preview": {"pages": len(preview_pages), "generation": gen},
        "changes": [c.model_dump() for c in session.changes],
        "applied_count": sum(1 for c in session.changes if c.status == "applied"),
        "converter": result_docs["converter"],
        "notes": list(ctx.job.notes),
        "ai_status": session.ai_status,
    }
    session.result = result
    return result


def _build_and_validate(session: Session, ctx: JobContext, texts: dict[str, str], docx_path: Path,
                        out_dir: Path, attempt: dict) -> dict[str, Any]:
    resume = session.resume
    assert resume is not None
    for tries in range(2):
        ctx.step("generating_docx")
        if resume.file_type == "docx":
            write_tailored_docx(session.resume_path, resume, texts, docx_path,
                                spacing_factor=attempt["spacing"], collapse_empty=attempt["collapse"])
        else:
            build_docx_from_blocks(resume, texts, session.resume_path, docx_path, spacing_factor=attempt["spacing"])

        ctx.step("validating_docx")
        d_text = docx_text(docx_path)
        docx_val = validate_document_text("DOCX", d_text, resume, texts)
        gen_fp = docx_fingerprint(python_docx.Document(str(docx_path)))

        ctx.step("generating_pdf")
        pdf_path, used = docx_to_pdf(docx_path, out_dir)

        ctx.step("validating_pdf")
        p_text = pdf_text(pdf_path)
        pdf_val = validate_document_text("PDF", p_text, resume, texts)
        pdf_pages = pdf_page_count(pdf_path)
        if pdf_pages == 0 or len(p_text.strip()) < 100:
            pdf_val["passed"] = False
            pdf_val["checks"].append({"check": "PDF is not blank", "passed": False, "detail": "no text"})
        import pymupdf
        with pymupdf.open(str(pdf_path)) as pd:
            pdf_fp = pdf_fingerprint(pd)
        consistency = validate_consistency(d_text, p_text, gen_fp.images, pdf_fp.images)

        ctx.step("visual_validation")
        heading_texts = [b.text for b in resume.blocks if b.role == "section_heading"]
        orig_min = min(resume.fingerprint.font_sizes) if resume.fingerprint.font_sizes else None
        visual = validate_visual(pdf_path, resume.fingerprint, heading_texts, orig_min)
        ctx.step("page_count")
        ok = docx_val["passed"] and pdf_val["passed"] and visual["passed"]
        if ok or tries == 1:
            break
        ctx.note("Validation found problems in the generated document; regenerating once.")
    if resume.file_type == "pdf":
        gen_fp = pdf_fp
        gen_fp.sections = [b.text for b in resume.blocks if b.role == "section_heading"]
    else:
        gen_fp.sections = [texts.get(b.id, b.text).strip().rstrip(":") for b in resume.blocks if b.role == "section_heading"]
    gen_fp.page_count = pdf_pages
    return {"docx_path": docx_path, "pdf_path": pdf_path, "pdf_text": p_text, "pdf_pages": pdf_pages,
            "docx_validation": docx_val, "pdf_validation": pdf_val, "consistency": consistency,
            "visual": visual, "fingerprint": gen_fp, "converter": used}


def _condense_changes(session: Session, texts: dict[str, str], ctx: JobContext) -> int:
    resume = session.resume
    longer: list[Change] = [c for c in session.changes if c.status in ("accepted", "applied")
                            and len(c.suggested) > len(c.original) + 5]
    if not longer:
        return 0
    items = [{"id": c.block_id, "text": c.suggested, "target_chars": len(c.original)} for c in longer]
    condensed = ai.condense(items)
    changed = 0
    for c in longer:
        new = condensed.get(c.block_id)
        if not new or len(new) >= len(c.suggested):
            continue
        v = check_change(resume.block(c.block_id), new, resume.full_text, session.keyword_evidence)
        keeps_keywords = all(re.search(re.escape(k), new, re.I) for k in c.jd_keywords)
        if v.passed and keeps_keywords:
            c.suggested = new
            c.reason += " (Condensed to keep the original page count.)"
            changed += 1
    return changed


def _cleanup_old_generations(session: Session, keep: int) -> None:
    for d in session.directory.glob("gen*"):
        if d.is_dir() and d.name != f"gen{keep}":
            shutil.rmtree(d, ignore_errors=True)
    preview = session.directory / "preview"
    for f in preview.glob("g*_p*.png"):
        if not f.name.startswith(f"g{keep}_"):
            f.unlink(missing_ok=True)
