"""Anti-fabrication validation of suggested changes against the source resume.

A suggestion fails if it introduces anything the source resume does not support: numbers,
metrics, dates, years of experience, technologies/tools that are not evidenced, JD-only
keywords, or new proper nouns (companies, clients, products).
"""
from __future__ import annotations

import re

from ..ats.lexicon import ALIASES, ALL_TERMS, category_of
from ..ats.matching import aliases_of, find_term, match_keyword, normalize_text, stem
from ..core.models import Block, ChangeValidation, KeywordEvidence
from ..parsing.sections import DATE_ANY_RE, split_skill_items, strip_bullet

NUMBER_WORDS = {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
                "fifteen", "twenty", "thirty", "fifty", "hundred", "hundreds", "thousand", "thousands", "million",
                "millions", "billion", "dozens", "double", "doubled", "tripled", "half"}
NUM_RE = re.compile(r"(?<![A-Za-z])[$€£]?\d[\d,.]*\s*(?:%|\+|k|m|x|bn)?(?![A-Za-z])", re.I)
YEARS_RE = re.compile(r"\b(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b", re.I)
SAFE_CAPITALIZED = {"I", "API", "APIs", "UI", "UX", "IT", "QA", "HR", "CEO", "CTO", "KPI", "KPIs", "SLA", "SLAs",
                    "B2B", "B2C", "SaaS", "PaaS", "IaaS", "MVP", "ROI", "R&D", "Agile"}
# Rank used as a title: "Senior Python Developer", "Lead Engineer", "principal developer" — not the verb "lead".
_RANK = r"(Senior|Sr\.?|Lead|Principal|Staff|Head|Chief|Junior|Jr\.?|senior|principal|junior)"
_ROLE_NOUN = r"(?:developer|engineer|architect|programmer|consultant|analyst|manager|designer|scientist)s?"
SENIORITY_RE = re.compile(rf"\b{_RANK}\s+(?=[A-Z]|(?:[\w+#./-]+\s+){{0,3}}{_ROLE_NOUN}\b)")
_ALL_LEXICON = sorted({*ALL_TERMS, *ALIASES.keys(), *(a for v in ALIASES.values() for a in v)}, key=len, reverse=True)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", normalize_text(s)).strip().lower()


def _numbers(text: str) -> set[str]:
    out = set()
    for m in NUM_RE.finditer(text):
        tok = re.sub(r"[\s,]", "", m.group(0)).lower().rstrip(".")
        if tok:
            out.add(tok)
    return out


def _num_core(tok: str) -> str:
    return re.sub(r"[^\d.]", "", tok).rstrip(".")


def _capitalized_tokens(text: str) -> list[str]:
    tokens = []
    for sentence in re.split(r"(?<=[.!?:;])\s+|\n|\t|\s[|•·]\s", text):
        words = re.findall(r"[A-Za-z][\w+#.&/-]*", sentence)
        for i, w in enumerate(words):
            w = w.rstrip(".,/-")
            if i == 0 or not w:
                continue
            if w[0].isupper() or re.search(r"\d", w) or any(c.isupper() for c in w[1:]):
                tokens.append(w)
    return tokens


def _in_source(token: str, source_norm: str) -> bool:
    t = token.lower()
    if t in source_norm:
        return True
    return stem(t) in source_norm


def check_change(block: Block, suggested: str, source_text: str, evidence: list[KeywordEvidence]) -> ChangeValidation:
    issues: list[str] = []
    original = block.text
    source_norm = _norm(source_text)
    sugg_body = strip_bullet(suggested)[1]

    if not sugg_body.strip():
        return ChangeValidation(passed=False, issues=["Suggestion is empty."])
    if len(suggested) > max(2.0 * len(original), len(original) + 160):
        issues.append("Suggestion is much longer than the original paragraph.")

    # Numbers / metrics must already exist in the resume (and those in the original must be kept).
    src_nums = {_num_core(n) for n in _numbers(source_text)}
    for n in _numbers(suggested):
        if _num_core(n) and _num_core(n) not in src_nums:
            issues.append(f"Adds the number '{n}', which is not in your resume.")
    sugg_nums = {_num_core(n) for n in _numbers(suggested)}
    for n in _numbers(original):
        if _num_core(n) and _num_core(n) not in sugg_nums:
            issues.append(f"Drops the figure '{n}' from the original text.")
    for w in re.findall(r"[A-Za-z]+", suggested.lower()):
        if w in NUMBER_WORDS and w not in source_norm.split() and not re.search(rf"\b{w}\b", source_norm):
            issues.append(f"Adds the quantity '{w}', which is not in your resume.")
    for m in YEARS_RE.finditer(suggested):
        if not re.search(rf"\b{m.group(1)}\s*\+?\s*(?:years?|yrs?)\b", source_norm):
            issues.append(f"Claims '{m.group(0)}' of experience, which is not stated in your resume.")
    for m in DATE_ANY_RE.finditer(suggested):
        if _norm(m.group(0)) not in source_norm:
            issues.append(f"Adds the date '{m.group(0)}', which is not in your resume.")

    # JD keywords that are not evidenced must never be introduced.
    for ev in evidence:
        if ev.usable:
            continue
        variants = [ev.term, *aliases_of(ev.term)]
        if any(find_term(v, suggested) for v in variants) and not any(find_term(v, original) for v in variants):
            issues.append(f"Adds '{ev.term}', which is not evidenced in your resume.")

    # Known technologies/skills must be evidenced by the source resume.
    usable_terms = {e.term.lower() for e in evidence if e.usable}
    reported: set[str] = set()
    for term in _ALL_LEXICON:
        if term.lower() in reported or not find_term(term, suggested) or find_term(term, original):
            continue
        cat = category_of(term)
        mtype, _ = match_keyword(term, source_text)
        ok = mtype in ("exact", "alias") or (mtype == "related" and term.lower() in usable_terms)
        if not ok and cat != "soft_skill" and not (term.lower() in usable_terms):
            reported.add(term.lower())
            issues.append(f"Adds '{term}', which your resume does not evidence.")

    # Seniority / rank words are claims about the candidate (checked anywhere, including sentence starts).
    for m in SENIORITY_RE.finditer(suggested):
        w = m.group(1)
        if not re.search(rf"\b{re.escape(w.lower().rstrip('.'))}\b", source_norm):
            issues.append(f"Claims the seniority '{w}', which your resume does not state.")

    # Rewrites must not silently drop technologies or named things from the original paragraph.
    for term in _ALL_LEXICON:
        if find_term(term, original) and not find_term(term, suggested) and \
                not any(find_term(a, suggested) for a in aliases_of(term)):
            if not any(term.lower() in o.lower() and find_term(o, suggested) for o in _ALL_LEXICON if o != term):
                issues.append(f"Drops '{term}' from the original text.")
    sugg_norm = _norm(suggested)
    for tok in dict.fromkeys(_capitalized_tokens(strip_bullet(original)[1])):
        if tok not in SAFE_CAPITALIZED and not _in_source(tok, sugg_norm) and \
                match_keyword(tok, suggested)[0] not in ("exact", "alias"):  # "RESTful" -> "REST APIs" is fine
            issues.append(f"Drops '{tok}' from the original text.")

    # New proper nouns (companies, clients, products) are not allowed.
    usable_norm = " ".join(usable_terms)
    for tok in _capitalized_tokens(sugg_body):
        if tok in SAFE_CAPITALIZED or tok.lower() in reported:
            continue
        if not _in_source(tok, source_norm) and tok.lower() not in usable_norm:
            reported.add(tok.lower())
            issues.append(f"Introduces '{tok}', which does not appear in your resume.")

    # Headlines: every significant word must come from the resume.
    if block.role == "headline":
        for w in re.findall(r"[A-Za-z][A-Za-z+#.-]{2,}", suggested):
            if not _in_source(w, source_norm) and w.lower() not in usable_norm and w.lower() not in {"and", "with", "for"}:
                issues.append(f"Headline word '{w}' is not supported by your resume.")
                break

    # Skill lines: only reorder/regroup existing items, keep the label.
    if block.role == "skills":
        orig_label = original.split(":", 1)[0] if ":" in original[:40] else None
        sugg_label = suggested.split(":", 1)[0] if ":" in suggested[:40] else None
        if orig_label and _norm(orig_label) != _norm(sugg_label or ""):
            issues.append("Changes the skills category label.")
        for item in split_skill_items(suggested):
            if not find_term(item, source_text) and match_keyword(item, source_text)[0] not in ("exact", "alias"):
                issues.append(f"Adds the skill '{item}', which is not in your resume.")
        dropped = {i for i in split_skill_items(original)
                   if match_keyword(i, suggested)[0] not in ("exact", "alias")
                   and _norm(i) not in _norm(suggested)}
        if dropped:
            issues.append(f"Removes skills from the line: {', '.join(sorted(dropped))}.")

    # Deduplicate while preserving order.
    seen, unique = set(), []
    for i in issues:
        if i not in seen:
            seen.add(i)
            unique.append(i)
    return ChangeValidation(passed=not unique, issues=unique)
