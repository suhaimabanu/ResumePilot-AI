"""Deterministic, explainable ATS Compatibility Score (0-100).

Weights:  Keyword Match 30 | Required Skills 20 | Experience Alignment 15 |
          Responsibilities Alignment 15 | Education/Certifications 10 | Formatting/Parsing 10

The same function scores the original and the tailored resume, so before/after numbers are
directly comparable. Gemini never decides any of these numbers.
"""
from __future__ import annotations

import re
from datetime import date

from ..core.models import JDAnalysis, ResumeSource
from ..parsing.sections import DATE_RANGE_RE, EMAIL_RE, PHONE_RE, SINGLE_DATE
from .matching import COVERAGE_CREDIT, count_term, match_keyword, significant_tokens

WEIGHTS = {
    "keyword_match": 30,
    "required_skills": 20,
    "experience_alignment": 15,
    "responsibilities_alignment": 15,
    "education_certifications": 10,
    "formatting_parsing": 10,
}
LABELS = {
    "keyword_match": "Keyword Match",
    "required_skills": "Required Skills",
    "experience_alignment": "Experience Alignment",
    "responsibilities_alignment": "Responsibilities Alignment",
    "education_certifications": "Education / Certifications",
    "formatting_parsing": "Formatting / Parsing",
}
IMPORTANCE_WEIGHT = {"required": 2.0, "preferred": 1.0, "general": 1.0}
STUFFING_LIMIT = 6
MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
DEGREE_LEVELS = [
    (4, r"ph\.?\s?d|doctorate|doctor of"),
    (3, r"master'?s?|m\.?\s?sc|m\.?\s?s\.|mba|m\.?\s?tech|m\.?\s?eng|m\.?\s?a\.|msc"),
    (2, r"bachelor'?s?|b\.?\s?sc|b\.?\s?s\.|b\.?\s?tech|b\.?\s?e\.|b\.?\s?a\.|bsc|undergraduate degree|\bbs\b|\bba\b"),
    (1, r"associate'?s? degree|diploma"),
]


def _keyword_rows(jd: JDAnalysis, text: str) -> list[dict]:
    rows = []
    for kw in jd.keywords:
        mtype, evidence = match_keyword(kw.term, text)
        rows.append({
            "term": kw.term, "category": kw.category, "importance": kw.importance,
            "match_type": mtype, "credit": COVERAGE_CREDIT[mtype], "evidence": evidence,
            "status": "matched" if mtype in ("exact", "alias") else ("partial" if mtype != "none" else "missing"),
            "count": count_term(kw.term, text),
        })
    return rows


def _coverage(rows: list[dict]) -> dict:
    total_w = sum(IMPORTANCE_WEIGHT[r["importance"]] for r in rows) or 0
    got_w = sum(IMPORTANCE_WEIGHT[r["importance"]] * r["credit"] for r in rows)
    return {
        "total": len(rows),
        "matched": sum(1 for r in rows if r["status"] == "matched"),
        "partial": sum(1 for r in rows if r["status"] == "partial"),
        "missing": sum(1 for r in rows if r["status"] == "missing"),
        "percent": round(100 * got_w / total_w, 1) if total_w else 100.0,
        "matched_terms": [r["term"] for r in rows if r["status"] == "matched"],
        "partial_terms": [r["term"] for r in rows if r["status"] == "partial"],
        "missing_terms": [r["term"] for r in rows if r["status"] == "missing"],
        "ratio": (got_w / total_w) if total_w else 1.0,
    }


def _parse_date(s: str, end: bool) -> tuple[int, int] | None:
    s = s.strip().lower()
    if re.match(r"present|current|now|today|ongoing|date", s):
        t = date.today()
        return t.year, t.month
    m = re.match(r"([a-z]{3})[a-z]*\.?\s*,?\s*(\d{4})", s)
    if m and m.group(1) in MONTHS:
        return int(m.group(2)), MONTHS[m.group(1)]
    m = re.match(r"(\d{1,2})\s*[/.-]\s*(\d{4})", s)
    if m:
        return int(m.group(2)), max(1, min(12, int(m.group(1))))
    m = re.match(r"(\d{4})\s*[/.-]\s*(\d{1,2})", s)
    if m:
        return int(m.group(1)), max(1, min(12, int(m.group(2))))
    m = re.match(r"((?:19|20)\d{2})", s)
    if m:
        return int(m.group(1)), 12 if end else 1
    return None


def experience_years(resume: ResumeSource, text_by_block: dict[str, str]) -> float:
    intervals = []
    candidates = [e.dates for e in resume.experience if e.dates]
    if not candidates:
        candidates = [m.group(0) for b in resume.blocks if b.section == "experience"
                      for m in DATE_RANGE_RE.finditer(text_by_block.get(b.id, b.text))]
    for rng in candidates:
        parts = re.split(r"\s*(?:[-–—~]|to|until|till)\s*", rng, maxsplit=1, flags=re.I)
        if len(parts) != 2:
            continue
        a, b = _parse_date(parts[0], False), _parse_date(parts[1], True)
        if a and b:
            start, stop = a[0] * 12 + a[1], b[0] * 12 + b[1]
            if stop >= start:
                intervals.append((start, stop))
    intervals.sort()
    merged: list[list[int]] = []
    for s, e in intervals:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return round(sum(e - s + 1 for s, e in merged) / 12, 1)


def _degree_level(text: str) -> int:
    for level, pat in DEGREE_LEVELS:
        if re.search(pat, text, re.I):
            return level
    return 0


def score_resume(resume: ResumeSource, jd: JDAnalysis, text_by_block: dict[str, str] | None = None,
                 page_count: int | None = None) -> dict:
    """Score a resume (original or tailored). text_by_block overrides block texts (tailored version)."""
    text_by_block = text_by_block or {b.id: b.text for b in resume.blocks}
    blocks_text = [text_by_block.get(b.id, b.text) for b in resume.blocks]
    text = "\n".join(t for t in blocks_text if t.strip())
    cats: dict[str, dict] = {}

    # 1. Keyword match ---------------------------------------------------------------------------
    rows = _keyword_rows(jd, text)
    cov = _coverage(rows)
    stuffed = [r["term"] for r in rows if r["count"] > STUFFING_LIMIT]
    penalty = min(3.0, 0.5 * len(stuffed))
    kw_score = max(0.0, WEIGHTS["keyword_match"] * cov["ratio"] - penalty)
    cats["keyword_match"] = {
        "score": kw_score,
        "explanation": (f"{cov['matched']} of {cov['total']} JD keywords matched, {cov['partial']} partially "
                        f"(weighted coverage {cov['percent']}%; required keywords count double)."
                        + (f" Penalty -{penalty:g} for repetitive use of: {', '.join(stuffed)}." if stuffed else "")),
        "matched": cov["matched_terms"], "partial": cov["partial_terms"], "missing": cov["missing_terms"],
        "stuffing": stuffed,
    }

    # 2. Required skills ---------------------------------------------------------------------------
    req_rows = [r for r in rows if r["importance"] == "required" and r["category"] not in ("soft_skill", "responsibility")]
    if req_rows:
        req_cov = _coverage([dict(r, importance="general") for r in req_rows])
        req_score = WEIGHTS["required_skills"] * req_cov["ratio"]
        req_expl = f"{req_cov['matched']} of {req_cov['total']} required skills matched, {req_cov['partial']} partially."
    else:
        req_cov = {"matched_terms": [], "partial_terms": [], "missing_terms": [], "percent": 100.0, "total": 0, "matched": 0}
        req_score = WEIGHTS["required_skills"] * cov["ratio"]
        req_expl = "The JD lists no explicit required skills; overall keyword coverage was used."
    cats["required_skills"] = {
        "score": req_score, "explanation": req_expl,
        "matched": req_cov["matched_terms"], "partial": req_cov["partial_terms"], "missing": req_cov["missing_terms"],
    }

    # 3. Experience alignment ----------------------------------------------------------------------
    years = experience_years(resume, text_by_block)
    if jd.years_experience:
        years_ratio = min(1.0, years / jd.years_experience) if years else 0.0
        years_expl = f"{years:g} years of dated experience vs {jd.years_experience:g}+ required"
    else:
        years_ratio = 1.0 if resume.experience or years else 0.5
        years_expl = f"{years:g} years of dated experience (no minimum stated in the JD)"
    title_texts = [text_by_block.get(b.id, b.text) for b in resume.blocks if b.role in ("headline", "experience_header")]
    jd_title_tokens = set(significant_tokens(jd.job_title)) - {"senior", "junior", "lead", "principal", "staff"}
    best_title = 0.0
    if jd_title_tokens:
        for t in title_texts:
            toks = set(significant_tokens(t))
            best_title = max(best_title, len(jd_title_tokens & toks) / len(jd_title_tokens))
    else:
        best_title = 1.0
    seniority_words = {"senior", "lead", "principal", "staff", "head", "manager", "director"}
    jd_senior = any(w in jd.job_title.lower().split() for w in seniority_words)
    has_senior = any(w in " ".join(title_texts).lower().split() for w in seniority_words)
    seniority = 1.0 if (not jd_senior or has_senior) else 0.4
    exp_score = WEIGHTS["experience_alignment"] * (0.5 * years_ratio + 0.35 * best_title + 0.15 * seniority)
    cats["experience_alignment"] = {
        "score": exp_score,
        "explanation": (f"{years_expl}; job-title similarity {round(best_title * 100)}%"
                        + ("; seniority level matches." if seniority == 1.0 else "; seniority level differs.")),
        "years": years, "required_years": jd.years_experience, "title_similarity": round(best_title * 100),
    }

    # 4. Responsibilities alignment ----------------------------------------------------------------
    resp = [r for r in jd.responsibilities if len(significant_tokens(r)) >= 2][:15]
    sentences = [t for t, b in zip(blocks_text, resume.blocks) if t.strip() and b.kind != "heading"]
    doc_tokens = set(significant_tokens(text))
    resp_rows = []
    for r in resp:
        rt = set(significant_tokens(r))
        best = max((len(rt & set(significant_tokens(s))) / len(rt) for s in sentences), default=0.0)
        overall = len(rt & doc_tokens) / len(rt)
        resp_rows.append({"responsibility": r, "alignment": round(100 * (0.6 * best + 0.4 * overall))})
    resp_ratio = (sum(x["alignment"] for x in resp_rows) / (100 * len(resp_rows))) if resp_rows else 0.7
    cats["responsibilities_alignment"] = {
        "score": WEIGHTS["responsibilities_alignment"] * min(1.0, resp_ratio * 1.15),
        "explanation": (f"Average alignment of your experience with {len(resp_rows)} JD responsibilities is "
                        f"{round(resp_ratio * 100)}%." if resp_rows else "No responsibilities found in the JD; neutral score used."),
        "items": resp_rows,
    }

    # 5. Education / certifications ----------------------------------------------------------------
    edu_text = "\n".join(text_by_block.get(b.id, b.text) for b in resume.blocks if b.section in ("education", "certifications"))
    req_level = max((_degree_level(e) for e in jd.education_requirements), default=0)
    have_level = _degree_level(edu_text) or _degree_level(text)
    edu_ratio = 1.0 if req_level == 0 else (1.0 if have_level >= req_level else (0.5 if have_level else 0.0))
    cert_terms = [k.term for k in jd.keywords if k.category == "certification"]
    cert_lines = jd.certifications
    if cert_terms or cert_lines:
        hits = sum(1 for c in cert_terms if match_keyword(c, text)[0] != "none")
        line_hit = any(set(significant_tokens(c)) & set(significant_tokens(edu_text)) - {"certif", "certification"}
                       and re.search(r"certif", edu_text, re.I) for c in cert_lines)
        cert_ratio = max(hits / len(cert_terms) if cert_terms else 0.0, 1.0 if line_hit else 0.0)
        edu_score = 7 * edu_ratio + 3 * cert_ratio
        cert_expl = f"certification requirement {'met' if cert_ratio >= 1 else ('partly met' if cert_ratio else 'not evidenced')}"
    else:
        edu_score = 10 * edu_ratio
        cert_expl = "no certifications requested"
    names = {0: "none detected", 1: "associate/diploma", 2: "bachelor's", 3: "master's", 4: "doctorate"}
    cats["education_certifications"] = {
        "score": edu_score,
        "explanation": (f"Degree: {names[have_level]}"
                        + (f" vs {names[req_level]} required" if req_level else " (no degree requirement detected)")
                        + f"; {cert_expl}."),
    }

    # 6. Formatting / parsing ----------------------------------------------------------------------
    checks = []

    def check(ok: bool, pts: float, label: str) -> float:
        checks.append({"check": label, "passed": bool(ok), "points": pts})
        return pts if ok else 0.0

    fmt = 0.0
    fmt += check(bool(resume.name), 1.0, "Candidate name detected")
    fmt += check(bool(EMAIL_RE.search(text)), 1.5, "Email address present")
    fmt += check(bool(PHONE_RE.search(text)), 1.0, "Phone number present")
    std = {s.key for s in resume.sections} & {"summary", "skills", "experience", "education", "projects", "certifications"}
    fmt += check(len(std) >= 3, 2.0, f"Standard section headings ({len(std)} recognized)")
    dated = sum(1 for e in resume.experience if e.dates)
    fmt += check(bool(resume.experience) and dated == len(resume.experience), 1.5, "Every experience entry has dates")
    fmt += check(len(text.split()) >= 150, 1.0, "Enough machine-readable text")
    fmt += check(sum(1 for b in resume.blocks if b.kind == "bullet") >= 3, 1.0, "Uses bullet points for achievements")
    pages = page_count or resume.page_count
    fmt += check(pages is None or pages <= 3, 1.0, f"Reasonable length ({pages or '?'} page(s))")
    cats["formatting_parsing"] = {
        "score": fmt,
        "explanation": f"{sum(1 for c in checks if c['passed'])} of {len(checks)} parsing checks passed.",
        "checks": checks,
    }

    categories = []
    for key, weight in WEIGHTS.items():
        c = cats[key]
        categories.append({"key": key, "label": LABELS[key], "max": weight,
                           "score": round(min(weight, c.pop("score")), 1), **c})
    total = round(sum(c["score"] for c in categories))
    return {
        "total": int(total),
        "categories": categories,
        "keyword_coverage": {k: v for k, v in cov.items() if k != "ratio"},
        "required_coverage": {"percent": req_cov["percent"], "matched": req_cov.get("matched", 0),
                              "total": req_cov.get("total", 0)},
        "keywords": rows,
    }


def compare_scores(before: dict, after: dict) -> dict:
    return {
        "original": before["total"],
        "tailored": after["total"],
        "improvement": after["total"] - before["total"],
        "keyword_coverage": {
            "original": before["keyword_coverage"]["percent"],
            "tailored": after["keyword_coverage"]["percent"],
            "improvement": round(after["keyword_coverage"]["percent"] - before["keyword_coverage"]["percent"], 1),
            "matched_before": before["keyword_coverage"]["matched"],
            "matched_after": after["keyword_coverage"]["matched"],
            "total": after["keyword_coverage"]["total"],
        },
        "required_coverage": {
            "original": before["required_coverage"]["percent"],
            "tailored": after["required_coverage"]["percent"],
        },
        "categories": [
            {"key": a["key"], "label": a["label"], "max": a["max"], "original": b["score"], "tailored": a["score"]}
            for b, a in zip(before["categories"], after["categories"])
        ],
    }
