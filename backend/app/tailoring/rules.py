"""Deterministic, always-factual suggestions (used alongside Gemini, and alone if Gemini is unavailable).

1. Skill ordering — move JD-relevant skills (that the resume already lists) to the front of each line.
2. Terminology alignment — when the resume uses a true alias of a JD keyword (e.g. "Postgres" vs
   "PostgreSQL"), suggest the JD's spelling. Only ALIASES (exact equivalents) are used, never RELATED.
"""
from __future__ import annotations

import re

from ..ats.lexicon import category_of
from ..ats.matching import aliases_of, find_term, match_keyword, term_regex
from ..core.models import JDAnalysis, KeywordEvidence, ResumeSource
from ..parsing.sections import split_skill_items

RANK = {"required": 0, "preferred": 1, "general": 2}


def _skill_line_reorder(text: str, jd: JDAnalysis) -> str | None:
    label = ""
    body = text
    if ":" in text[:40]:
        label, body = text.split(":", 1)
        label += ":"
    items = split_skill_items(text)
    if len(items) < 3:
        return None
    sep = " | " if "|" in body else (" • " if "•" in body else ("; " if ";" in body else ", "))

    def rank(item: str) -> int:
        best = 3
        for kw in jd.keywords:
            if match_keyword(kw.term, item)[0] in ("exact", "alias"):
                best = min(best, RANK[kw.importance])
        return best

    ordered = sorted(items, key=lambda i: (rank(i), items.index(i)))
    if ordered == items:
        return None
    lead = re.match(r"^\s*", body).group(0) if label else ""
    trail = "." if body.rstrip().endswith(".") else ""
    return f"{label}{lead or (' ' if label else '')}{sep.join(ordered)}{trail}"


RENAMEABLE_CATEGORIES = {"programming_language", "framework", "database", "cloud", "tool"}
RENAMEABLE_TERMS = {"rest api"}


def _align_terms(text: str, evidence: list[KeywordEvidence]) -> tuple[str, list[str]]:
    """Only technology *names* are renamed (Postgres -> PostgreSQL); descriptive phrases are left
    to the AI because a mechanical swap would break grammar or shift meaning."""
    new = text
    used = []
    for ev in evidence:
        if ev.status != "supported" or ev.match_type != "alias":
            continue
        if category_of(ev.term) not in RENAMEABLE_CATEGORIES and ev.term.lower() not in RENAMEABLE_TERMS:
            continue
        if find_term(ev.term, new):
            continue
        for alias in sorted(aliases_of(ev.term), key=len, reverse=True):
            if len(alias) <= 3:
                continue  # very short aliases (e.g. "ML") are left alone
            m = term_regex(alias).search(new)
            if not m:
                continue
            matched = m.group(0)
            replacement = ev.term
            if matched.lower().endswith("s") and not alias.lower().endswith("s") and not ev.term.lower().endswith("s"):
                replacement += "s"
            elif alias.lower().endswith("s") and not ev.term.lower().endswith("s"):
                replacement += "s"
            new = new[: m.start()] + replacement + new[m.end():]
            used.append(ev.term)
            break
    return new, used


def rule_suggestions(resume: ResumeSource, jd: JDAnalysis, evidence: list[KeywordEvidence],
                     locked_ids: set[str]) -> list[dict]:
    out: list[dict] = []
    for b in resume.blocks:
        if not b.editable or not b.text.strip() or b.id in locked_ids:
            continue
        if b.role == "skills":
            new = _skill_line_reorder(b.text, jd)
            if new:
                moved = [kw.term for kw in jd.keywords if find_term(kw.term, b.text)][:6]
                out.append({"id": b.id, "text": new, "keywords": moved, "source_claims": [],
                            "reason": "Moves the skills this job asks for to the front of the line so recruiters "
                                      "and ATS parsers see them first. No skills were added or removed."})
            continue
        new, used = _align_terms(b.text, evidence)
        if used and new != b.text:
            out.append({"id": b.id, "text": new, "keywords": used, "source_claims": [],
                        "reason": f"Uses the job description's exact wording ({', '.join(used)}) for a skill your "
                                  "resume already shows under a different name."})
    return out
