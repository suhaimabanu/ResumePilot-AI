"""Build the source-of-truth ResumeSource from the actual uploaded file."""
from __future__ import annotations

import hashlib
import re
import secrets
from pathlib import Path

import docx

from ..core.jobs import UserFacingError
from ..core.models import ResumeSource, SourceClaim
from .docx_parser import parse_docx
from .docx_xml import enumerate_paragraphs, paragraph_text
from .pdf_parser import parse_pdf, pdf_text
from .sections import classify, strip_bullet

UNREADABLE = "We couldn't reliably read your resume. Please upload another file or try a DOCX version."


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_resume(path: Path, file_type: str, filename: str) -> ResumeSource:
    try:
        if file_type == "docx":
            raw, fingerprint, app_pages = parse_docx(path)
            page_count, ocr_used = app_pages, False
        else:
            raw, fingerprint, page_count, ocr_used = parse_pdf(path)
    except UserFacingError:
        raise
    except Exception as exc:
        raise UserFacingError(UNREADABLE) from exc

    blocks, info = classify(raw)
    text_blocks = [b for b in blocks if b.text.strip()]
    total_words = sum(len(b.text.split()) for b in text_blocks)
    if len(text_blocks) < 3 or total_words < 40:
        raise UserFacingError(UNREADABLE)

    resume = ResumeSource(
        resume_id=secrets.token_hex(8),
        source_hash=file_hash(path),
        filename=filename,
        file_type=file_type,  # type: ignore[arg-type]
        page_count=page_count,
        ocr_used=ocr_used,
        blocks=blocks,
        name=info["name"],
        headline=info["headline"],
        contact=info["contact"],
        sections=info["sections"],
        experience=info["experience"],
        projects=info["projects"],
        education=info["education"],
        certifications=info["certifications"],
        skills=info["skills"],
        fingerprint=fingerprint,
        structuring="heuristic",
    )
    fingerprint.sections = [s.title for s in resume.sections]
    if not resume.name:
        resume.warnings.append("Candidate name could not be detected automatically.")
    if not resume.sections:
        resume.warnings.append("No standard section headings were detected.")
    if ocr_used:
        resume.warnings.append("Text was recognised with OCR; please double-check the result.")
    resume.claims = heuristic_claims(resume)
    return resume


def heuristic_claims(resume: ResumeSource) -> list[SourceClaim]:
    """Deterministic source claims: every skill item and every factual content paragraph."""
    claims: list[SourceClaim] = []
    n = 0

    def add(text: str, block_ids: list[str], evidence: str) -> None:
        nonlocal n
        n += 1
        claims.append(SourceClaim(id=f"SRC{n:03d}", claim=text, block_ids=block_ids, evidence=evidence))

    skill_blocks = {b.id: b for b in resume.blocks if b.section == "skills" and b.kind != "heading"}
    for skill in resume.skills:
        bid = next((i for i, b in skill_blocks.items() if skill.lower() in b.text.lower()), None)
        add(f"Skill: {skill}", [bid] if bid else [], skill)
    for b in resume.blocks:
        if b.editable and b.section != "skills" and b.text.strip():
            body = strip_bullet(b.text)[1].strip()
            add(body[:240], [b.id], body)
    return claims


def extract_document_text(path: Path, file_type: str) -> str:
    """Plain text of a document (used for JD files and for content validation)."""
    if file_type == "pdf":
        return pdf_text(path)
    if file_type == "docx":
        d = docx.Document(str(path))
        return "\n".join(paragraph_text(h.element) for h in enumerate_paragraphs(d))
    raise ValueError(file_type)


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
