"""Resume completeness validation: the tailored resume must be the COMPLETE original resume.

Compares the source-of-truth model with the final (tailored) block texts. Fails if any entry,
company, title, date, section or locked paragraph was lost or altered, or if the output is
suspiciously short / summary-only.
"""
from __future__ import annotations

import re

from ..core.models import ResumeSource


def _alnum(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def validate_completeness(resume: ResumeSource, texts: dict[str, str]) -> dict:
    checks: list[dict] = []

    def add(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    missing_ids = [b.id for b in resume.blocks if b.id not in texts]
    add("Every source paragraph present", not missing_ids, f"{len(missing_ids)} missing" if missing_ids else
        f"{len(resume.blocks)} paragraphs")

    altered_locked = [b.id for b in resume.blocks if not b.editable and texts.get(b.id, b.text) != b.text]
    add("Locked content unchanged (name, contact, headings, companies, titles, dates, education)",
        not altered_locked, ", ".join(altered_locked[:6]) or "unchanged")

    emptied = [b.id for b in resume.blocks if b.text.strip() and not texts.get(b.id, "").strip()]
    add("No paragraph emptied", not emptied, ", ".join(emptied[:6]) or "none")

    all_text = _alnum("\n".join(texts.get(b.id, b.text) for b in resume.blocks))
    # A name/contact that was never in the source text (e.g. a header banner image, kept unchanged
    # in the template) has nothing to lose — only text that was detected must survive.
    not_in_text = "not found in the original text (e.g. part of an image), kept as in the original"
    add("Candidate name present", not resume.name or _alnum(resume.name) in all_text, resume.name or not_in_text)
    add("Contact information present",
        all(_alnum(v) in all_text for v in (resume.contact.email, resume.contact.phone) if v),
        resume.contact.email or resume.contact.phone or not_in_text)

    has_summary = any(b.role == "summary" for b in resume.blocks)
    if has_summary:
        ok = all(texts.get(b.id, "").strip() for b in resume.blocks if b.role == "summary")
        add("Summary present", ok)
    if resume.skills:
        ok = all(texts.get(b.id, "").strip() for b in resume.blocks if b.section == "skills" and b.text.strip())
        add("Skills present", ok, f"{len(resume.skills)} skills")

    for label, entries in (("experience", resume.experience), ("project", resume.projects), ("education", resume.education)):
        if not entries:
            continue
        lost = []
        for e in entries:
            header_ok = all(texts.get(h) == resume.block(h).text for h in e.header_block_ids if resume.block(h))
            fields_ok = all(_alnum(v) in all_text for v in (e.title, e.organization, e.dates) if v)
            bullets_ok = all(len(texts.get(bid, "").split()) >= 3 or len(resume.block(bid).text.split()) < 3
                             for bid in e.bullet_block_ids if resume.block(bid))
            if not (header_ok and fields_ok and bullets_ok):
                lost.append(e.label)
        add(f"All {len(entries)} {label} entries preserved (titles, organizations, dates, bullets)", not lost,
            ", ".join(lost[:4]) or f"Source: {len(entries)} · Generated: {len(entries)}")

    if resume.certifications:
        ok = all(_alnum(c) in all_text for c in resume.certifications)
        add("Certifications preserved", ok, f"{len(resume.certifications)} certification(s)")

    heading_ok = all(texts.get(b.id) == b.text for b in resume.blocks if b.role == "section_heading")
    add(f"All {len(resume.sections)} sections preserved", heading_ok)

    src_words = sum(len(b.text.split()) for b in resume.blocks)
    out_words = sum(len(texts.get(b.id, "").split()) for b in resume.blocks)
    ratio = out_words / src_words if src_words else 0
    add("Output is not truncated or summary-only", ratio >= 0.75, f"{out_words} words vs {src_words} in the original")

    return {"passed": all(c["passed"] for c in checks), "checks": checks}
