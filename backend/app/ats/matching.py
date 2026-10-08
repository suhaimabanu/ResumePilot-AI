"""Deterministic keyword matching: exact, normalized, alias, related (partial) and token overlap."""
from __future__ import annotations

import re
from functools import lru_cache

from .lexicon import ALIASES, CASE_SENSITIVE, RELATED

STOPWORDS = set("""
a an the and or of to in on for with by from at as is are be been being was were will would can could should may
might must shall this that these those it its into over under about across within without per via than then also
such other more most less least very well good great strong excellent proven solid deep hands hands-on ability able
experience experienced years year plus etc using use used work working including include includes our we you your
they their them who what which when where while all any each both either some new etc. e.g i.e related relevant
skills skill knowledge understanding familiarity proficiency proficient expertise background degree role team teams
candidate candidates position job company environment looking join help required requirements preferred nice have
has had must-have bonus responsibilities qualifications will responsible ensure across based like eg ie
""".split())

_DASHES = str.maketrans({"–": "-", "—": "-", "‐": "-", "‑": "-", "’": "'", "‘": "'", "“": '"', "”": '"', " ": " "})


def normalize_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.translate(_DASHES))


def stem(word: str) -> str:
    w = word.lower()
    for suf, rep in (("ations", ""), ("ation", ""), ("ments", ""), ("ment", ""), ("ings", ""), ("ing", ""),
                     ("ies", "y"), ("ied", "y"), ("ers", ""), ("er", ""), ("es", ""), ("ed", ""), ("s", "")):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)] + rep
    return w


def significant_tokens(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.]*[A-Za-z0-9+#]|[A-Za-z]", normalize_text(text))
    return [stem(w) for w in words if w.lower() not in STOPWORDS and len(w) > 2]


@lru_cache(maxsize=4096)
def term_regex(term: str) -> re.Pattern:
    term = normalize_text(term).strip()
    parts = []
    for ch in term:
        if ch in " -":
            parts.append(r"[\s\-]*" if ch == "-" else r"[\s\-]+")
        else:
            parts.append(re.escape(ch))
    body = "".join(parts).replace(r"[\s\-]+[\s\-]*", r"[\s\-]+")
    plural = r"(?:s|es)?" if term[-1:].isalpha() and len(term) > 2 else ""
    pattern = rf"(?<![A-Za-z0-9+#.]){body}{plural}(?![A-Za-z0-9+#]|\.[A-Za-z])"
    flags = 0 if term in CASE_SENSITIVE else re.IGNORECASE
    return re.compile(pattern, flags)


def find_term(term: str, text: str) -> re.Match | None:
    if not term.strip():
        return None
    return term_regex(term).search(normalize_text(text))


def count_term(term: str, text: str) -> int:
    if not term.strip():
        return 0
    return len(term_regex(term).findall(normalize_text(text)))


@lru_cache(maxsize=1)
def _alias_groups() -> list[set[str]]:
    groups: list[set[str]] = []
    for canonical, aliases in ALIASES.items():
        groups.append({canonical, *aliases})
    return groups


def aliases_of(term: str) -> list[str]:
    low = term.lower().strip()
    out: list[str] = []
    for g in _alias_groups():
        if low in {x.lower() for x in g}:
            out.extend(x for x in g if x.lower() != low and x not in out)
    return out


def related_of(term: str) -> list[str]:
    low = term.lower().strip()
    for key, rel in RELATED.items():
        if key.lower() == low or low in {a.lower() for a in aliases_of(key)}:
            return rel
    return []


def evidence_snippet(text: str, match: re.Match | None, width: int = 160) -> str:
    if not match:
        return ""
    norm = normalize_text(text)
    start = max(norm.rfind("\n", 0, match.start()) + 1, match.start() - width // 2)
    end_nl = norm.find("\n", match.end())
    end = min(end_nl if end_nl != -1 else len(norm), match.end() + width // 2)
    return norm[start:end].strip()


def match_keyword(term: str, text: str) -> tuple[str, str]:
    """Returns (match_type, evidence) where match_type in exact|alias|related|partial_tokens|none."""
    if m := find_term(term, text):
        return "exact", evidence_snippet(text, m)
    for alias in aliases_of(term):
        if m := find_term(alias, text):
            return "alias", evidence_snippet(text, m)
    for rel in related_of(term):
        if m := find_term(rel, text):
            return "related", evidence_snippet(text, m)
    toks = [t for t in significant_tokens(term)]
    if len(toks) >= 2:
        text_toks = set(significant_tokens(text))
        hit = [t for t in toks if t in text_toks]
        if len(hit) / len(toks) >= 0.5:
            return "partial_tokens", ""
    return "none", ""


COVERAGE_CREDIT = {"exact": 1.0, "alias": 0.75, "related": 0.5, "partial_tokens": 0.5, "evidence": 0.5, "none": 0.0}
