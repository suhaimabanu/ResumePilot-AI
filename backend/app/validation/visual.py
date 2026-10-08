"""Visual validation of the generated PDF (rendered layout checks)."""
from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

from ..core.models import TemplateFingerprint
from ..parsing.pdf_parser import _clean_font


def _issue(severity: str, code: str, message: str, page: int | None = None) -> dict:
    return {"severity": severity, "code": code, "message": message, "page": page}


def validate_visual(pdf_path: Path, original_fp: TemplateFingerprint, heading_texts: list[str],
                    original_min_font: float | None = None) -> dict:
    issues: list[dict] = []
    doc = fitz.open(str(pdf_path))
    fonts_used: set[str] = set()
    square_images = 0
    images_total = 0
    try:
        headings = {h.strip().lower() for h in heading_texts if h.strip()}
        for pno, page in enumerate(doc, start=1):
            rect = page.rect
            data = page.get_text("dict")
            lines = []
            tiny_chars = total_chars = 0
            for b in data["blocks"]:
                if b.get("type") != 0:
                    continue
                for l in b["lines"]:
                    text = "".join(s["text"] for s in l["spans"]).strip()
                    if not text:
                        continue
                    lines.append((fitz.Rect(l["bbox"]), text))
                    for s in l["spans"]:
                        if not s["text"].strip():
                            continue
                        fonts_used.add(_clean_font(s["font"]))
                        n = len(s["text"].strip())
                        total_chars += n
                        if s["size"] < 5.5:
                            tiny_chars += n
                        x0, y0, x1, y1 = s["bbox"]
                        if x0 < -1 or y0 < -1 or x1 > rect.width + 1 or y1 > rect.height + 1:
                            issues.append(_issue("critical", "out_of_bounds",
                                                 f"Text extends outside the page: “{s['text'][:40]}”", pno))
            infos = [i for i in page.get_image_info() if (i["bbox"][2] - i["bbox"][0]) > 4]
            images_total += len(infos)
            for info in infos:
                x0, y0, x1, y1 = info["bbox"]
                w, h = x1 - x0, y1 - y0
                if h and 0.6 <= w / h <= 1.6 and min(w, h) >= 40:
                    square_images += 1
                if x1 > rect.width + 2 or y1 > rect.height + 2 or x0 < -2:
                    issues.append(_issue("critical", "image_clipped", "An image extends beyond the page edge.", pno))

            # Blank page
            if not lines and not infos:
                pix = page.get_pixmap(dpi=30, colorspace=fitz.csGRAY)
                ink = sum(1 for v in pix.samples if v < 230) / max(1, len(pix.samples))
                if ink < 0.003:
                    issues.append(_issue("critical", "blank_page", "This page is blank.", pno))
                continue

            # Overlapping text lines
            overlaps = 0
            for i in range(len(lines)):
                ra = lines[i][0]
                for j in range(i + 1, len(lines)):
                    rb = lines[j][0]
                    inter = fitz.Rect(ra) & rb
                    if inter.is_empty:
                        continue
                    smaller = min(ra.get_area(), rb.get_area()) or 1
                    if inter.get_area() / smaller > 0.35 and lines[i][1] != lines[j][1]:
                        overlaps += 1
            if overlaps:
                issues.append(_issue("critical" if overlaps > 2 else "warning", "overlap",
                                     f"{overlaps} overlapping text line(s) detected.", pno))

            if total_chars and tiny_chars / total_chars > 0.05 and (original_min_font is None or original_min_font >= 5.5):
                issues.append(_issue("critical", "tiny_text", "Text is too small to read comfortably.", pno))

            # Orphaned heading at the bottom of a page
            if pno < doc.page_count and lines:
                last = max(lines, key=lambda l: l[0].y1)
                if last[1].strip().lower() in headings:
                    issues.append(_issue("warning", "orphan_heading",
                                         f"Section heading “{last[1]}” is stranded at the bottom of the page.", pno))

        if doc.page_count > 1:
            last_lines = [l for b in doc[-1].get_text("dict")["blocks"] if b.get("type") == 0 for l in b["lines"]
                          if "".join(s["text"] for s in l["spans"]).strip()]
            if 0 < len(last_lines) <= 3:
                issues.append(_issue("warning", "sparse_last_page",
                                     "The last page holds only a few lines (excessive whitespace).", doc.page_count))

        if original_fp.profile_photo and square_images == 0:
            issues.append(_issue("critical", "photo_missing", "The profile photo is missing from the PDF."))
        if original_fp.images and images_total == 0:
            issues.append(_issue("critical", "images_missing", "Images from the original resume are missing."))
        expected_fonts = {f.lower() for f in original_fp.fonts}
        if expected_fonts and fonts_used and not any(
                any(e.split()[0] in u.lower() for e in expected_fonts) for u in fonts_used):
            issues.append(_issue("warning", "font_substitution",
                                 f"Fonts were substituted when rendering (expected {', '.join(sorted(original_fp.fonts)[:3])})."))
        pages = doc.page_count
    finally:
        doc.close()
    critical = [i for i in issues if i["severity"] == "critical"]
    return {
        "passed": not critical,
        "pages_checked": pages,
        "issues": issues,
        "fonts_rendered": sorted(fonts_used),
        "images_rendered": images_total,
        "profile_photo_rendered": square_images > 0,
    }
