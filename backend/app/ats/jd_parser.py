"""Deterministic Job Description parsing (always run; merged with Gemini's richer analysis)."""
from __future__ import annotations

import re

from ..core.models import JDAnalysis, JDKeyword
from .lexicon import ALL_TERMS, NOT_EXTRACTABLE, category_of
from .matching import find_term, normalize_text

SECTION_PATTERNS = {
    "responsibilities": r"responsibilit|what you('|’)?ll do|what you will do|the role|duties|your impact|day to day|you will",
    "required": r"requirement|qualification|what we('|’)?re looking for|must have|must-have|you have|about you|skills|who you are|what you bring|minimum",
    "preferred": r"nice to have|nice-to-have|preferred|bonus|plus|desired|good to have|would be great",
}
DEGREE_RE = re.compile(r"\b(bachelor'?s?|master'?s?|ph\.?d|doctorate|b\.?sc|m\.?sc|b\.?s\.|m\.?s\.|mba|b\.?tech|m\.?tech|b\.?e\.|associate'?s? degree|degree)\b", re.I)
YEARS_RE = re.compile(r"(\d{1,2})\s*\+?\s*(?:-|to|–)?\s*(?:\d{1,2})?\s*\+?\s*years?", re.I)


def _heading_kind(line: str) -> str | None:
    t = line.strip().rstrip(":").lower()
    if len(t.split()) > 8 or not t:
        return None
    for kind, pat in SECTION_PATTERNS.items():
        if re.search(pat, t):
            return kind
    return None


def parse_jd_text(text: str) -> JDAnalysis:
    text = normalize_text(text)
    lines = [l.strip() for l in text.splitlines()]
    lines = [l for l in lines if l]
    jd = JDAnalysis(source="heuristic")
    if lines:
        first = re.sub(r"^(job\s*title|position|role)\s*:\s*", "", lines[0], flags=re.I)
        if len(first.split()) <= 12:
            jd.job_title = re.split(r"\s+[-–—|@]\s+|\s+at\s+", first)[0].strip()
            parts = re.split(r"\s+[-–—|@]\s+|\s+at\s+", first)
            if len(parts) > 1:
                jd.company = parts[-1].strip()

    current = None
    buckets: dict[str, list[str]] = {"responsibilities": [], "required": [], "preferred": [], "other": []}
    for line in lines[1:]:
        kind = _heading_kind(line)
        if kind and (line.endswith(":") or len(line.split()) <= 5):
            current = kind
            continue
        item = re.sub(r"^[\-\*•●▪◦·]\s*|^\d+[.)]\s*", "", line).strip()
        if not item:
            continue
        buckets[current or "other"].append(item)

    jd.responsibilities = buckets["responsibilities"] or [s for s in buckets["other"] if len(s.split()) >= 5][:12]
    jd.qualifications = buckets["required"]
    for m in YEARS_RE.finditer(text):
        val = float(m.group(1))
        if 0 < val <= 30:
            jd.years_experience = max(jd.years_experience or 0, val)
    clean = [re.sub(r"^[\-\*•●▪◦·]\s*|^\d+[.)]\s*", "", l).strip() for l in lines]
    jd.education_requirements = [l for l in clean if DEGREE_RE.search(l) and len(l.split()) <= 40][:4]
    jd.certifications = [l for l in clean if re.search(r"certif", l, re.I) and len(l.split()) <= 30][:4]

    req_text = "\n".join(buckets["required"] + buckets["responsibilities"])
    pref_text = "\n".join(buckets["preferred"])
    seen: set[str] = set()
    for term in ALL_TERMS:
        if term.lower() in NOT_EXTRACTABLE or term.lower() in seen:
            continue
        if not find_term(term, text):
            continue
        seen.add(term.lower())
        if find_term(term, req_text):
            importance = "required"
        elif find_term(term, pref_text):
            importance = "preferred"
        else:
            importance = "general"
        jd.keywords.append(JDKeyword(term=term, category=category_of(term), importance=importance))
    # Drop terms that are substrings of a longer extracted term found at the same place (e.g. "Spring" in "Spring Boot").
    terms = [k.term for k in jd.keywords]
    jd.keywords = [k for k in jd.keywords
                   if not any(o != k.term and k.term.lower() in o.lower() and not find_term(k.term, re.sub(re.escape(o), " ", text, flags=re.I))
                              for o in terms)]
    jd.required_skills = [k.term for k in jd.keywords if k.importance == "required" and k.category != "soft_skill"]
    jd.preferred_skills = [k.term for k in jd.keywords if k.importance == "preferred"]
    jd.soft_skills = [k.term for k in jd.keywords if k.category == "soft_skill"]
    return jd
