"""Decide, deterministically, which JD keywords the source resume supports.

The JD is never evidence. A keyword is usable in tailoring only if the source resume contains
it (exactly or by a true alias), or a defensible related term, or an AI-provided quote that is
verified to exist verbatim in the source resume.
"""
from __future__ import annotations

import re

from ..core.models import JDAnalysis, KeywordEvidence
from .matching import match_keyword, normalize_text


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", normalize_text(s).lower()).strip(" .,;:")


def verify_quote(quote: str, source_text: str) -> bool:
    q = _norm(quote)
    return len(q.split()) >= 2 and q in _norm(source_text)


def assess_keywords(jd: JDAnalysis, source_text: str, ai_evidence: dict[str, str] | None = None) -> list[KeywordEvidence]:
    ai_evidence = {k.lower(): v for k, v in (ai_evidence or {}).items()}
    results: list[KeywordEvidence] = []
    for kw in jd.keywords:
        mtype, snippet = match_keyword(kw.term, source_text)
        ev = KeywordEvidence(term=kw.term, category=kw.category, importance=kw.importance)
        if mtype in ("exact", "alias"):
            ev.status, ev.match_type, ev.evidence, ev.usable = "supported", mtype, snippet, True
            ev.explanation = (f"Found in your resume{' as an equivalent term' if mtype == 'alias' else ''}.")
        elif mtype == "related":
            ev.status, ev.match_type, ev.evidence, ev.usable = "partial", "related", snippet, True
            ev.explanation = "Your resume shows closely related experience; it can be emphasized carefully."
        else:
            quote = ai_evidence.get(kw.term.lower(), "")
            if quote and verify_quote(quote, source_text):
                ev.status, ev.match_type, ev.evidence, ev.usable = "partial", "evidence", quote.strip(), True
                ev.explanation = "Your resume describes this work without naming it explicitly."
            elif mtype == "partial_tokens":
                ev.status, ev.match_type = "partial", "partial_tokens"
                ev.explanation = ("Some related words appear in your resume, but there is no reliable evidence "
                                  "of this exact skill, so it was not added.")
            else:
                ev.status, ev.match_type = "missing", "none"
                ev.explanation = ("The uploaded resume does not provide reliable evidence of this. "
                                  "Not added to the tailored resume to avoid inventing experience.")
        results.append(ev)
    return results
