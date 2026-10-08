"""Build user-reviewable Change objects from AI + rule proposals, and apply user selections."""
from __future__ import annotations

import re

from ..ats.matching import find_term
from ..ats.scoring import score_resume
from ..core.models import Change, JDAnalysis, KeywordEvidence, ResumeSource
from ..parsing.sections import split_skill_items, strip_bullet
from ..validation.fact_check import check_change

SECTION_LABELS = {
    "header": "Headline", "summary": "Professional Summary", "skills": "Skills", "experience": "Experience",
    "projects": "Projects", "achievements": "Achievements", "volunteer": "Volunteer / Activities",
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _fix_prefix(original: str, suggested: str) -> str:
    """Keep the original manual bullet prefix (or lack of one)."""
    o_prefix, _ = strip_bullet(original)
    s_prefix, s_body = strip_bullet(suggested)
    if o_prefix:
        return o_prefix + s_body.lstrip()
    return s_body if s_prefix else suggested


def entry_labels(resume: ResumeSource) -> dict[str, str]:
    labels = {}
    for e in resume.experience + resume.projects:
        for bid in e.bullet_block_ids:
            labels[bid] = e.label
    return labels


def build_changes(resume: ResumeSource, jd: JDAnalysis, evidence: list[KeywordEvidence],
                  ai_props: list[dict], rule_props: list[dict], start_index: int = 1,
                  base_texts: dict[str, str] | None = None) -> tuple[list[Change], list[dict]]:
    """Returns (valid changes, blocked proposals)."""
    source_text = resume.full_text
    labels = entry_labels(resume)
    claims_by_block: dict[str, list[str]] = {}
    for c in resume.claims:
        for bid in c.block_ids:
            claims_by_block.setdefault(bid, []).append(c.id)
    claim_ids = {c.id: c for c in resume.claims}
    jd_terms = [k.term for k in jd.keywords]

    # AI proposals take precedence; rules fill blocks the AI left unchanged.
    by_block: dict[str, dict] = {}
    for p in ai_props:
        by_block[p["id"]] = dict(p, origin="ai")
    for p in rule_props:
        b = resume.block(p["id"])
        if b is None:
            continue
        existing = by_block.get(p["id"])
        if existing is None or _norm(existing["text"]) == _norm(b.text):
            by_block[p["id"]] = dict(p, origin="rules")

    base_texts = base_texts or {b.id: b.text for b in resume.blocks}
    base_precise = sum(c["score"] for c in score_resume(resume, jd, base_texts)["categories"])

    changes: list[Change] = []
    blocked: list[dict] = []
    idx = start_index
    for block in resume.blocks:
        prop = by_block.get(block.id)
        if not prop:
            continue
        suggested = _fix_prefix(block.text, prop["text"])
        if _norm(suggested) == _norm(block.text):
            continue
        validation = check_change(block, suggested, source_text, evidence)
        if not validation.passed:
            # One retry path for AI output: fall back to the rule proposal for that block if it is valid.
            rule = next((r for r in rule_props if r["id"] == block.id), None)
            if prop.get("origin") == "ai" and rule:
                alt = _fix_prefix(block.text, rule["text"])
                alt_val = check_change(block, alt, source_text, evidence)
                if alt_val.passed and _norm(alt) != _norm(block.text):
                    blocked.append({"block_id": block.id, "section": block.section, "suggested": suggested,
                                    "issues": validation.issues})
                    prop, suggested, validation = dict(rule, origin="rules"), alt, alt_val
            if not validation.passed:
                blocked.append({"block_id": block.id, "section": block.section, "suggested": suggested,
                                "issues": validation.issues})
                continue

        is_reorder = (block.role == "skills" and
                      sorted(i.lower() for i in split_skill_items(block.text)) ==
                      sorted(i.lower() for i in split_skill_items(suggested)))
        kws = [t for t in jd_terms if find_term(t, suggested)]
        newly = [t for t in kws if not find_term(t, block.text)]
        ai_kws = [k for k in prop.get("keywords", []) if any(k.lower() == t.lower() for t in kws)]
        jd_keywords = list(dict.fromkeys(newly + ai_kws + ([t for t in kws] if is_reorder else [])))[:8]
        claims = [c for c in prop.get("source_claims", []) if c in claim_ids]
        claims = list(dict.fromkeys(claims + claims_by_block.get(block.id, [])))[:6]

        trial = dict(base_texts)
        trial[block.id] = suggested
        scored = score_resume(resume, jd, trial)
        delta = sum(c["score"] for c in scored["categories"]) - base_precise
        impact = "high" if delta >= 1.5 else ("medium" if delta >= 0.5 else "low")

        changes.append(Change(
            change_id=f"CHG{idx:03d}",
            block_id=block.id,
            section=block.section,
            section_title=block.section_title or SECTION_LABELS.get(block.section, block.section.title()),
            entry_label=labels.get(block.id, ""),
            kind="reorder_skills" if is_reorder else "rewrite",
            original=block.text,
            suggested=suggested,
            reason=prop.get("reason") or "Improves alignment with the job description.",
            source_claims=claims,
            source_evidence=[claim_ids[c].evidence[:200] for c in claims if claim_ids[c].evidence][:4],
            jd_keywords=jd_keywords,
            impact=impact,
            validation=validation,
        ))
        idx += 1
    return changes, blocked


def final_texts(resume: ResumeSource, changes: list[Change]) -> dict[str, str]:
    texts = {b.id: b.text for b in resume.blocks}
    for c in changes:
        if c.status in ("accepted", "applied"):
            texts[c.block_id] = c.suggested
    return texts
