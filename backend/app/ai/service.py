"""High-level AI tasks. Gemini output is never trusted blindly: every field is validated
against the source resume / JD before it is used."""
from __future__ import annotations

import logging
import re

from ..ats.matching import find_term, normalize_text, significant_tokens
from ..core.models import Entry, JDAnalysis, JDKeyword, KeywordEvidence, ResumeSource, SourceClaim
from . import prompts
from .base import AIError, AIProvider, AIResponseError
from .gemini import GeminiProvider

log = logging.getLogger("ai.service")
_provider: AIProvider | None = None


def get_provider() -> AIProvider:
    global _provider
    if _provider is None:
        _provider = GeminiProvider()
    return _provider


def set_provider(provider: AIProvider | None) -> None:
    """Used by the test-suite to inject a fake provider."""
    global _provider
    _provider = provider


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", normalize_text(s or "")).strip().lower()


def _verbatim(fragment: str, haystack: str) -> bool:
    f = _norm(fragment).strip(" .,;:|")
    return bool(f) and f in _norm(haystack)


# ---------------------------------------------------------------------------------------------
# Resume structure + claims
# ---------------------------------------------------------------------------------------------
def refine_structure(resume: ResumeSource) -> list[str]:
    """Use Gemini to improve entry structure + claims. Returns notes. Keeps heuristics on failure."""
    provider = get_provider()
    if not provider.available:
        return ["AI structuring unavailable — used deterministic structure detection."]
    try:
        data = provider.generate_json(prompts.SYSTEM_FACTUAL, prompts.structure_prompt(resume), task="structure")
    except AIError as exc:
        log.warning("structure failed: %s", exc)
        return ["AI structuring failed — used deterministic structure detection."]

    notes: list[str] = []
    by_id = {b.id: b for b in resume.blocks}
    exp_block_ids = {b.id for b in resume.blocks if b.section == "experience" and b.kind not in ("heading", "empty")}

    ai_exp: list[Entry] = []
    valid = True
    for i, item in enumerate(data.get("experience") or []):
        if not isinstance(item, dict):
            valid = False
            break
        headers = [h for h in item.get("header_blocks") or [] if h in by_id]
        bullets = [h for h in item.get("bullet_blocks") or [] if h in by_id]
        header_text = " ".join(by_id[h].text for h in headers)
        fields = {k: str(item.get(k) or "").strip() for k in ("title", "company", "dates", "location")}
        if not headers or any(v and not _verbatim(v, header_text) for v in fields.values()):
            valid = False
            break
        ai_exp.append(Entry(entry_id=f"EXP{i + 1:02d}", title=fields["title"], organization=fields["company"],
                            dates=fields["dates"], location=fields["location"],
                            header_block_ids=headers, bullet_block_ids=bullets))
    covered = {b for e in ai_exp for b in e.header_block_ids + e.bullet_block_ids}
    if valid and ai_exp and exp_block_ids <= covered:
        if len(ai_exp) != len(resume.experience):
            notes.append(f"AI structuring found {len(ai_exp)} experience entries (heuristic found {len(resume.experience)}).")
        resume.experience = ai_exp
        resume.structuring = "ai"
    elif data.get("experience"):
        notes.append("AI experience structure failed verification — kept deterministic structure.")
        # Still adopt verified titles/companies for heuristic entries that share header blocks.
        for e in resume.experience:
            for a in ai_exp:
                if set(a.header_block_ids) & set(e.header_block_ids):
                    e.title, e.organization = a.title or e.title, a.organization or e.organization
                    e.dates = a.dates or e.dates

    for item in data.get("projects") or []:
        if not isinstance(item, dict):
            continue
        headers = set(item.get("header_blocks") or [])
        for p in resume.projects:
            if headers & set(p.header_block_ids):
                name = str(item.get("name") or "").strip()
                if name and _verbatim(name, " ".join(by_id[h].text for h in p.header_block_ids)):
                    p.title = name

    for item in data.get("education") or []:
        if not isinstance(item, dict):
            continue
        blocks = set(item.get("blocks") or [])
        for e in resume.education:
            if blocks & set(e.header_block_ids):
                text = " ".join(by_id[h].text for h in e.header_block_ids)
                deg, inst = str(item.get("degree") or ""), str(item.get("institution") or "")
                if deg and _verbatim(deg, text):
                    e.title = deg
                if inst and _verbatim(inst, text):
                    e.organization = inst

    full = resume.full_text
    certs = [c for c in (data.get("certifications") or []) if isinstance(c, str) and _verbatim(c, full)]
    if certs:
        resume.certifications = certs
    skills = [s for s in (data.get("skills") or []) if isinstance(s, str) and _verbatim(s, full)]
    if len(skills) >= len(resume.skills) * 0.7 and skills:
        resume.skills = list(dict.fromkeys(skills))

    claims: list[SourceClaim] = []
    dropped = 0
    for item in data.get("claims") or []:
        if not isinstance(item, dict):
            continue
        blocks = [b for b in item.get("blocks") or [] if b in by_id]
        quote = str(item.get("quote") or "")
        text = " ".join(by_id[b].text for b in blocks) if blocks else full
        if quote and _verbatim(quote, text):
            claims.append(SourceClaim(id="", claim=str(item.get("claim") or quote)[:240], block_ids=blocks, evidence=quote))
        else:
            dropped += 1
    if claims:
        # Keep deterministic claims too (skills + paragraphs), then append verified AI claims.
        base = list(resume.claims)
        merged = base + claims
        for i, c in enumerate(merged):
            c.id = f"SRC{i + 1:03d}"
        resume.claims = merged
    if dropped:
        notes.append(f"{dropped} AI claims were discarded because their quotes were not found in the resume.")
    return notes


# ---------------------------------------------------------------------------------------------
# Job description analysis
# ---------------------------------------------------------------------------------------------
def _in_jd(term: str, jd_text: str) -> bool:
    if find_term(term, jd_text):
        return True
    toks = significant_tokens(term)
    jd_toks = set(significant_tokens(jd_text))
    return bool(toks) and sum(t in jd_toks for t in toks) / len(toks) >= 0.67


def merge_jd(heuristic: JDAnalysis, data: dict, jd_text: str) -> tuple[JDAnalysis, dict[str, str], list[str]]:
    notes: list[str] = []
    jd = heuristic.model_copy(deep=True)
    jd.source = "ai"

    def str_list(key: str, limit: int = 20) -> list[str]:
        out = []
        for x in data.get(key) or []:
            if isinstance(x, str) and x.strip():
                out.append(x.strip())
        return out[:limit]

    if isinstance(data.get("job_title"), str) and data["job_title"].strip():
        jd.job_title = data["job_title"].strip()
    if isinstance(data.get("company"), str) and data["company"].strip():
        jd.company = data["company"].strip()
    y = data.get("years_experience")
    if isinstance(y, (int, float)) and 0 < y <= 30:
        jd.years_experience = float(y)
    for key in ("education_requirements", "certifications", "responsibilities", "qualifications",
                "soft_skills", "required_skills", "preferred_skills"):
        vals = str_list(key)
        if vals:
            setattr(jd, key, vals)

    existing = {k.term.lower(): k for k in jd.keywords}
    rejected = 0
    rank = {"required": 2, "preferred": 1, "general": 0}
    for item in data.get("keywords") or []:
        if not isinstance(item, dict):
            continue
        term = str(item.get("term") or "").strip()
        if not term or len(term) > 60:
            continue
        if not _in_jd(term, jd_text):
            rejected += 1
            continue
        importance = item.get("importance") if item.get("importance") in rank else "general"
        category = str(item.get("category") or "other")
        low = term.lower()
        if low in existing:
            k = existing[low]
            if rank[importance] > rank[k.importance]:
                k.importance = importance
            continue
        kw = JDKeyword(term=term, category=category, importance=importance)
        jd.keywords.append(kw)
        existing[low] = kw
    if rejected:
        notes.append(f"{rejected} AI keywords were ignored because they do not appear in the job description.")
    jd.keywords = jd.keywords[:45]
    evidence = {}
    for item in data.get("evidence") or []:
        if isinstance(item, dict) and item.get("term") and item.get("quote"):
            evidence[str(item["term"]).strip()] = str(item["quote"])
    return jd, evidence, notes


def analyze_jd(jd_text: str, resume: ResumeSource, heuristic: JDAnalysis) -> tuple[JDAnalysis, dict[str, str], list[str]]:
    provider = get_provider()
    if not provider.available:
        return heuristic, {}, ["AI job-description analysis unavailable — used deterministic keyword extraction."]
    try:
        data = provider.generate_json(prompts.SYSTEM_FACTUAL, prompts.jd_prompt(jd_text, resume), task="jd")
    except AIError as exc:
        log.warning("jd analysis failed: %s", exc)
        return heuristic, {}, ["AI job-description analysis failed — used deterministic keyword extraction."]
    return merge_jd(heuristic, data, jd_text)


# ---------------------------------------------------------------------------------------------
# Tailoring
# ---------------------------------------------------------------------------------------------
def tailor(resume: ResumeSource, jd: JDAnalysis, evidence: list[KeywordEvidence], locked_ids: set[str],
           style: str) -> tuple[list[dict], list[str]]:
    """Returns raw per-block proposals [{id, text, reason, source_claims, keywords}] and notes."""
    provider = get_provider()
    if not provider.available:
        return [], ["Gemini is not configured — only deterministic terminology/skill-order suggestions were generated."]
    prompt = prompts.tailor_prompt(resume, jd, evidence, resume.claims, locked_ids, style)
    editable_ids = {b.id for b in resume.blocks if b.editable and b.text.strip() and b.id not in locked_ids}
    notes: list[str] = []
    last_missing: set[str] = set()
    for attempt in range(2):
        try:
            data = provider.generate_json(prompts.SYSTEM_FACTUAL, prompt, task="tailor", temperature=0.5)
        except AIError as exc:
            log.warning("tailor failed: %s", exc)
            return [], ["AI tailoring failed — only deterministic suggestions were generated. Try Regenerate."]
        blocks = data.get("blocks")
        if not isinstance(blocks, list):
            notes.append("AI returned a malformed tailoring response; retried.")
            continue
        out = []
        for item in blocks:
            if not isinstance(item, dict) or item.get("id") not in editable_ids:
                continue
            text = item.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            out.append({
                "id": item["id"], "text": text.strip(),
                "reason": str(item.get("reason") or "")[:400],
                "source_claims": [c for c in item.get("source_claims") or [] if isinstance(c, str)],
                "keywords": [k for k in item.get("keywords") or [] if isinstance(k, str)],
            })
        returned = {o["id"] for o in out}
        last_missing = editable_ids - returned
        # A response that leaves (almost) every prose paragraph untouched is not a tailoring — retry once.
        prose = {b.id: b.text for b in resume.blocks if b.id in editable_ids and b.role != "skills"}
        rewritten = sum(1 for o in out if o["id"] in prose and _norm(o["text"]) != _norm(prose[o["id"]]))
        if prose and rewritten < max(1, 0.3 * len(prose)) and attempt == 0:
            log.warning("tailor response too weak (%d of %d paragraphs rewritten); retrying", rewritten, len(prose))
            continue
        if len(returned) >= 0.6 * len(editable_ids) or attempt == 1:
            if last_missing:
                notes.append(f"AI response omitted {len(last_missing)} paragraph(s); they keep their original text.")
            return out, notes
        notes.append("AI tailoring response was incomplete; retried.")
    return [], notes + ["AI tailoring response was incomplete."]


def repair(blocked: list[dict], resume: ResumeSource, jd: JDAnalysis) -> list[dict]:
    """One repair round for AI rewrites the fact-checker rejected: returns new proposals (re-checked by the caller)."""
    provider = get_provider()
    items = []
    for b in blocked:
        block = resume.block(b["block_id"])
        if block is not None and block.role != "skills":
            items.append({"id": block.id, "original": block.text, "rejected": b["suggested"], "issues": b["issues"][:6]})
    if not provider.available or not items:
        return []
    try:
        data = provider.generate_json(prompts.SYSTEM_FACTUAL, prompts.repair_prompt(items, jd), task="repair",
                                      temperature=0.3)
    except (AIError, AIResponseError) as exc:
        log.warning("repair failed: %s", exc)
        return []
    ids = {i["id"] for i in items}
    return [{"id": b["id"], "text": b["text"].strip(), "reason": str(b.get("reason") or "")[:400],
             "source_claims": [], "keywords": [k for k in b.get("keywords") or [] if isinstance(k, str)]}
            for b in data.get("blocks") or []
            if isinstance(b, dict) and b.get("id") in ids and isinstance(b.get("text"), str) and b["text"].strip()]


def condense(items: list[dict]) -> dict[str, str]:
    provider = get_provider()
    if not provider.available or not items:
        return {}
    try:
        data = provider.generate_json(prompts.SYSTEM_FACTUAL, prompts.condense_prompt(items), task="condense")
    except (AIError, AIResponseError):
        return {}
    ids = {i["id"] for i in items}
    return {b["id"]: b["text"] for b in data.get("blocks") or []
            if isinstance(b, dict) and b.get("id") in ids and isinstance(b.get("text"), str) and b["text"].strip()}
