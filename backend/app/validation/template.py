"""Template preservation report: original vs generated fingerprints + rendered layout similarity."""
from __future__ import annotations

from ..core.models import TemplateFingerprint


def _set_score(a: list, b: list) -> float:
    sa, sb = {str(x).lower() for x in a}, {str(x).lower() for x in b}
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


def _status(score: float) -> str:
    return "Preserved" if score >= 0.97 else ("Mostly preserved" if score >= 0.75 else "Changed")


def compare_templates(orig: TemplateFingerprint, gen: TemplateFingerprint, layout_similarity: float | None,
                      rebuilt: bool, visual: dict | None = None) -> dict:
    aspects: list[dict] = []
    limitations: list[str] = []

    def aspect(name: str, score: float, detail: str = "") -> None:
        aspects.append({"aspect": name, "score": round(score * 100), "status": _status(score), "detail": detail})

    margin_keys = set(orig.margins) & set(gen.margins)
    if margin_keys:
        tol = 0.12 if rebuilt else 0.02
        m_ok = sum(1 for k in margin_keys if abs(orig.margins[k] - gen.margins[k]) <= tol) / len(margin_keys)
    else:
        m_ok = 1.0 if not orig.margins else 0.5
    aspect("Margins", m_ok, ", ".join(f"{k} {gen.margins.get(k)}in" for k in sorted(margin_keys)))
    aspect("Page size", 1.0 if (orig.page_size == gen.page_size or not orig.page_size) else 0.0, gen.page_size or "")
    aspect("Fonts", _set_score(orig.fonts, gen.fonts), ", ".join(gen.fonts[:4]))
    aspect("Font sizes", _set_score(orig.font_sizes, gen.font_sizes))
    aspect("Colors", _set_score(orig.colors, gen.colors))
    aspect("Sections", _set_score(orig.sections, gen.sections) if orig.sections else 1.0, f"{len(gen.sections)} sections")
    aspect("Tables", 1.0 if orig.tables == gen.tables else 0.0, f"{gen.tables} table(s)")
    aspect("Columns", 1.0 if orig.columns == gen.columns else 0.0, f"{gen.columns} column(s)")
    img_score = 1.0 if orig.images == gen.images else (0.5 if gen.images else 0.0)
    aspect("Images", img_score, f"{gen.images} of {orig.images}")
    if orig.profile_photo:
        photo_ok = gen.profile_photo and (visual is None or visual.get("profile_photo_rendered", True))
        aspect("Profile Photo", 1.0 if photo_ok else 0.0, "detected in DOCX and PDF" if photo_ok else "missing")
    if orig.headers or orig.footers:
        aspect("Headers / Footers", 1.0 if (orig.headers, orig.footers) == (gen.headers, gen.footers) else 0.0)
    if orig.text_boxes:
        aspect("Text boxes", 1.0 if orig.text_boxes == gen.text_boxes else 0.0)
    if layout_similarity is not None:
        aspect("Rendered layout", layout_similarity, f"{round(layout_similarity * 100)}% visual similarity")

    if rebuilt:
        limitations.append("The original was a PDF, which has no editable template. The layout was rebuilt from "
                           "measured fonts, sizes, colours, margins and spacing; multi-column layouts, graphics "
                           "and decorative shapes cannot be reproduced exactly. Upload a DOCX for maximum fidelity.")
    for a in aspects:
        if a["status"] == "Changed":
            limitations.append(f"{a['aspect']} could not be preserved exactly.")
    overall = sum(a["score"] for a in aspects) / len(aspects) if aspects else 100
    level = "High" if overall >= 90 else ("Medium" if overall >= 70 else "Low")
    return {"score": round(overall), "level": level, "aspects": aspects, "limitations": limitations}
