"""Content validation of generated documents against the expected tailored resume."""
from __future__ import annotations

import difflib
import re

from ..core.models import ResumeSource
from ..parsing.sections import strip_bullet

# Names that only exist in our demo fixtures. If they show up in output for a real resume
# that does not contain them, demo data leaked into production.
DEMO_MARKERS = ["Jordan Avery", "Northwind Analytics", "Bluebird Logistics", "Copperleaf Studio",
                "John Doe", "Jane Doe", "Jane Smith", "Acme Corp", "Lorem ipsum"]


def alnum(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _block_present(block_text: str, doc_alnum: str, doc_tokens: list[str]) -> tuple[bool, float]:
    body = strip_bullet(block_text)[1]
    key = alnum(body)
    if not key:
        return True, 1.0
    if key in doc_alnum:
        return True, 1.0
    toks = re.findall(r"[a-z0-9]+", body.lower())
    if not toks:
        return True, 1.0
    # Fuzzy: best matching window of the document tokens.
    n = len(toks)
    best = 0.0
    first = toks[0]
    starts = [i for i, t in enumerate(doc_tokens) if t == first] or range(0, max(1, len(doc_tokens) - n + 1), max(1, n // 2))
    for i in starts:
        window = doc_tokens[max(0, i - 2): i + n + 2]
        best = max(best, difflib.SequenceMatcher(None, toks, window, autojunk=False).ratio())
        if best > 0.97:
            break
    return best >= 0.9, round(best, 3)


def critical_fields(resume: ResumeSource) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    if resume.name:
        fields.append(("Name", resume.name))
    if resume.contact.email:
        fields.append(("Email", resume.contact.email))
    if resume.contact.phone:
        fields.append(("Phone", resume.contact.phone))
    for e in resume.experience:
        for label, v in (("Company", e.organization), ("Job title", e.title), ("Dates", e.dates)):
            if v:
                fields.append((label, v))
    for e in resume.education:
        for label, v in (("Education", e.title), ("Institution", e.organization)):
            if v:
                fields.append((label, v))
    for c in resume.certifications:
        fields.append(("Certification", c))
    for s in resume.sections:
        fields.append(("Section", s.title))
    return fields


def validate_document_text(kind: str, extracted: str, resume: ResumeSource, texts: dict[str, str]) -> dict:
    doc_alnum = alnum(extracted)
    doc_tokens = re.findall(r"[a-z0-9]+", extracted.lower())
    missing_blocks, fuzzy = [], []
    for b in resume.blocks:
        t = texts.get(b.id, b.text)
        if not t.strip():
            continue
        ok, ratio = _block_present(t, doc_alnum, doc_tokens)
        if not ok:
            missing_blocks.append({"block_id": b.id, "section": b.section, "text": t[:120], "similarity": ratio})
        elif ratio < 1.0:
            fuzzy.append(b.id)
    missing_fields = [{"field": f, "value": v} for f, v in critical_fields(resume) if alnum(v) and alnum(v) not in doc_alnum]
    expected_len = sum(len(alnum(strip_bullet(texts.get(b.id, b.text))[1])) for b in resume.blocks)
    ratio = len(doc_alnum) / expected_len if expected_len else 0
    checks = [
        {"check": "All resume paragraphs present", "passed": not missing_blocks,
         "detail": f"{len(missing_blocks)} missing" if missing_blocks else "complete"},
        {"check": "Name, contact, companies, titles, dates, sections present", "passed": not missing_fields,
         "detail": ", ".join(f"{m['field']}: {m['value']}" for m in missing_fields[:5]) or "all present"},
        {"check": "Output is not truncated", "passed": ratio >= 0.9,
         "detail": f"{round(ratio * 100)}% of expected text length"},
    ]
    return {
        "document": kind,
        "passed": all(c["passed"] for c in checks),
        "checks": checks,
        "missing_blocks": missing_blocks[:20],
        "missing_fields": missing_fields[:20],
        "fuzzy_matches": len(fuzzy),
    }


def validate_consistency(docx_text: str, pdf_text: str, docx_images: int, pdf_images: int) -> dict:
    a, b = alnum(docx_text), alnum(pdf_text)
    # Word-level similarity (order-tolerant enough for header/footer placement differences)
    ta, tb = re.findall(r"[a-z0-9]+", docx_text.lower()), re.findall(r"[a-z0-9]+", pdf_text.lower())
    sim = difflib.SequenceMatcher(None, ta, tb, autojunk=False).ratio() if ta and tb else 0.0
    from collections import Counter
    ca, cb = Counter(ta), Counter(tb)
    missing_in_pdf = sum((ca - cb).values())
    coverage = 1 - missing_in_pdf / max(1, sum(ca.values()))
    checks = [
        {"check": "PDF contains the DOCX text", "passed": coverage >= 0.97, "detail": f"{round(coverage * 100, 1)}% of words"},
        {"check": "Text order consistent", "passed": sim >= 0.85, "detail": f"{round(sim * 100, 1)}% sequence similarity"},
        {"check": "Images present in both", "passed": (docx_images == 0) == (pdf_images == 0),
         "detail": f"DOCX {docx_images} / PDF {pdf_images}"},
    ]
    return {"passed": all(c["passed"] for c in checks), "checks": checks,
            "length_ratio": round(len(b) / len(a), 3) if a else None}


def validate_identity(resume: ResumeSource, texts: dict[str, str], output_text: str) -> dict:
    """Ensure the output is the uploaded candidate's resume (not demo/default data)."""
    out = alnum(output_text)
    src = alnum(resume.full_text)
    issues = []
    if resume.name and alnum(resume.name) not in out:
        issues.append("The candidate's name is missing from the output.")
    for e in resume.experience:
        if e.organization and alnum(e.organization) not in out:
            issues.append(f"Employer '{e.organization}' is missing from the output.")
        if e.title and alnum(e.title) not in out:
            issues.append(f"Job title '{e.title}' is missing from the output.")
    for marker in DEMO_MARKERS:
        if alnum(marker) in out and alnum(marker) not in src:
            issues.append("Sample/demo data was detected in the output.")
            break
    final_alnum = alnum("\n".join(texts.values()))
    if final_alnum and src and difflib.SequenceMatcher(None, src[:4000], final_alnum[:4000], autojunk=False).quick_ratio() < 0.6:
        issues.append("The tailored content diverges too much from the uploaded resume.")
    return {"passed": not issues, "issues": issues}
