"""Parse an uploaded PDF into raw paragraphs + fingerprint, with OCR fallback for scanned files."""
from __future__ import annotations

import os
import re
import statistics
from pathlib import Path

import pymupdf as fitz

from ..core.config import settings
from ..core.jobs import UserFacingError
from ..core.models import BlockStyle, TemplateFingerprint
from .sections import BULLET_PREFIX_RE, RawParagraph

PUA_RE = re.compile(r"^[-•▪●◦∙•●▪■◦►▸➢➤✓✔]$")


def _color_hex(c: int) -> str:
    return f"{(c >> 16) & 255:02X}{(c >> 8) & 255:02X}{c & 255:02X}"


def _is_bold(span: dict) -> bool:
    return bool(span.get("flags", 0) & 16) or bool(re.search(r"bold|black|heavy|semibold", span.get("font", ""), re.I))


def _is_italic(span: dict) -> bool:
    return bool(span.get("flags", 0) & 2) or bool(re.search(r"italic|oblique", span.get("font", ""), re.I))


def _clean_font(name: str) -> str:
    name = name.split("+", 1)[-1]
    name = re.sub(r"[-,](Bold|Italic|BoldItalic|Regular|Medium|Light|Semibold|SemiBold|Black|Oblique|MT|PS).*$", "", name)
    return re.sub(r"(MT|PSMT|PS)$", "", name)


def _ordered_blocks(page: fitz.Page, textpage=None) -> list[dict]:
    data = page.get_text("dict", textpage=textpage) if textpage else page.get_text("dict")
    blocks = [b for b in data["blocks"] if b.get("type") == 0 and any(l["spans"] for l in b["lines"])]
    if not blocks:
        return []
    width = page.rect.width
    # Find a vertical gutter (sidebar / two-column layout) that no text block crosses.
    best = None
    for x in range(int(width * 0.22), int(width * 0.78), 3):
        crossing = [b for b in blocks if b["bbox"][0] < x - 2 < x + 2 < b["bbox"][2]]
        left = [b for b in blocks if b["bbox"][2] <= x]
        right = [b for b in blocks if b["bbox"][0] >= x]
        if len(left) >= 3 and len(right) >= 3:
            # Crossing blocks are tolerated only above the columns (full-width header).
            col_top = min(b["bbox"][1] for b in left + right)
            if all(b["bbox"][3] <= col_top + 4 for b in crossing) or not crossing:
                score = min(len(left), len(right))
                if best is None or score > best[1]:
                    best = (x, score, crossing)
    if best is None:
        return sorted(blocks, key=lambda b: (round(b["bbox"][1], 0), b["bbox"][0]))
    x, _, crossing = best
    top = sorted(crossing, key=lambda b: b["bbox"][1])
    left = sorted([b for b in blocks if b["bbox"][2] <= x], key=lambda b: b["bbox"][1])
    right = sorted([b for b in blocks if b["bbox"][0] >= x and b not in crossing], key=lambda b: b["bbox"][1])
    return top + left + right


def _line_text(line: dict) -> tuple[str, list[dict]]:
    spans = [s for s in line["spans"] if s["text"]]
    out = ""
    prev_x1 = None
    for s in spans:
        if prev_x1 is not None:
            gap = s["bbox"][0] - prev_x1
            if gap > max(18, s["size"] * 2.5):
                out = out.rstrip() + "\t"
            elif gap > s["size"] * 0.15 and not out.endswith((" ", "\t")) and not s["text"].startswith(" "):
                out += " "
        out += s["text"]
        prev_x1 = s["bbox"][2]
    return out, spans


def _paragraphs_from_page(page: fitz.Page, page_no: int, body_size: float | None, textpage=None) -> list[RawParagraph]:
    paras: list[RawParagraph] = []
    for block in _ordered_blocks(page, textpage):
        current: RawParagraph | None = None
        prev_line_bottom = None
        prev_bold = None
        for line in block["lines"]:
            text, spans = _line_text(line)
            if not text.strip():
                continue
            first = spans[0]
            is_bullet_glyph = bool(PUA_RE.match(first["text"].strip())) and len(spans) > 1
            if is_bullet_glyph:
                text = text[len(first["text"]):].lstrip()
                content_span = spans[1]
            else:
                content_span = first
            bold = all(_is_bold(s) for s in spans if s["text"].strip() and not PUA_RE.match(s["text"].strip()))
            starts_bullet = is_bullet_glyph or bool(BULLET_PREFIX_RE.match(text))
            if starts_bullet and not is_bullet_glyph:
                text = BULLET_PREFIX_RE.sub("", text, count=1)
            gap = (line["bbox"][1] - prev_line_bottom) if prev_line_bottom is not None else 0
            new_para = (
                current is None
                or starts_bullet
                or gap > content_span["size"] * 0.9
                or (prev_bold is not None and bold != prev_bold)
                or "\t" in text
                or (current is not None and "\t" in current.text)
            )
            if new_para:
                size = round(content_span["size"], 1)
                letters = re.sub(r"[^A-Za-z]", "", text)
                current = RawParagraph(
                    text=text.strip(),
                    location="body",
                    is_list=starts_bullet,
                    is_heading_style=bool(body_size and size >= body_size + 1.5 and len(text.split()) <= 6),
                    all_bold=bold,
                    all_caps=len(letters) >= 3 and letters.isupper(),
                    style=BlockStyle(
                        font=_clean_font(content_span.get("font", "")),
                        size=size,
                        bold=bold,
                        italic=_is_italic(content_span),
                        color=_color_hex(content_span.get("color", 0)),
                        page=page_no,
                        x0=round(line["bbox"][0], 1),
                        y0=round(line["bbox"][1], 1),
                        space_before=round(gap, 1) if gap > 0 else None,
                    ),
                )
                center = (line["bbox"][0] + line["bbox"][2]) / 2
                if abs(center - page.rect.width / 2) < 12 and (line["bbox"][2] - line["bbox"][0]) < page.rect.width * 0.7:
                    current.style.align = "center"
                paras.append(current)
            else:
                joined = current.text
                if joined.endswith("-") and text[:1].islower():
                    current.text = joined + text.strip()
                else:
                    current.text = joined + " " + text.strip()
            prev_line_bottom = line["bbox"][3]
            prev_bold = bold
    return paras


def _ocr_textpages(doc: fitz.Document) -> list:
    tessdata = os.environ.get("TESSDATA_PREFIX")
    if not tessdata and settings.tesseract_path:
        candidate = Path(settings.tesseract_path).parent / "tessdata"
        tessdata = str(candidate) if candidate.exists() else None
    if not settings.tesseract_path or not tessdata:
        raise UserFacingError(
            "We couldn't reliably read your resume: it looks like a scanned image and text recognition (OCR) "
            "is not available on this server. Please upload a DOCX or a text-based PDF."
        )
    try:
        return [page.get_textpage_ocr(language="eng", dpi=300, full=True, tessdata=tessdata) for page in doc]
    except Exception as exc:
        raise UserFacingError("We couldn't reliably read your scanned resume. Please upload a DOCX version.") from exc


def parse_pdf(path: Path) -> tuple[list[RawParagraph], TemplateFingerprint, int, bool]:
    doc = fitz.open(str(path))
    try:
        page_count = doc.page_count
        total_chars = sum(len(p.get_text("text").strip()) for p in doc)
        textpages = None
        ocr_used = False
        if total_chars < 80 * page_count:
            textpages = _ocr_textpages(doc)
            ocr_used = True
        sizes: list[float] = []
        for i, page in enumerate(doc):
            d = page.get_text("dict", textpage=textpages[i]) if textpages else page.get_text("dict")
            for b in d["blocks"]:
                for l in b.get("lines", []):
                    for s in l["spans"]:
                        if s["text"].strip():
                            sizes.extend([round(s["size"], 1)] * len(s["text"]))
        body_size = statistics.median(sizes) if sizes else None
        raw: list[RawParagraph] = []
        for i, page in enumerate(doc):
            raw.extend(_paragraphs_from_page(page, i + 1, body_size, textpages[i] if textpages else None))
        fp = pdf_fingerprint(doc)
        fp.paragraphs = len(raw)
        return raw, fp, page_count, ocr_used
    finally:
        doc.close()


def pdf_fingerprint(doc: fitz.Document) -> TemplateFingerprint:
    fp = TemplateFingerprint(page_count=doc.page_count)
    if doc.page_count:
        r = doc[0].rect
        w_in, h_in = r.width / 72, r.height / 72
        fp.page_size = "Letter" if abs(w_in - 8.5) < 0.1 and abs(h_in - 11) < 0.1 else (
            "A4" if abs(w_in - 8.27) < 0.1 and abs(h_in - 11.69) < 0.1 else f"{w_in:.2f}x{h_in:.2f}in")
    fonts, sizes, colors = set(), set(), set()
    images = 0
    profile = False
    min_x = min_y = 1e9
    max_x = max_y = 0.0
    for page in doc:
        d = page.get_text("dict")
        for b in d["blocks"]:
            if b.get("type") == 0:
                for l in b["lines"]:
                    for s in l["spans"]:
                        if not s["text"].strip():
                            continue
                        fonts.add(_clean_font(s["font"]))
                        sizes.add(round(s["size"], 1))
                        colors.add(_color_hex(s["color"]))
                        x0, y0, x1, y1 = s["bbox"]
                        min_x, min_y, max_x, max_y = min(min_x, x0), min(min_y, y0), max(max_x, x1), max(max_y, y1)
        for info in page.get_image_info():
            x0, y0, x1, y1 = info["bbox"]
            w, h = x1 - x0, y1 - y0
            if w < 4 or h < 4:
                continue
            images += 1
            if 0.6 <= w / h <= 1.6 and min(w, h) >= 40:
                profile = True
    if doc.page_count and max_x > 0:
        r = doc[0].rect
        fp.margins = {"left": round(min_x / 72, 2), "top": round(min_y / 72, 2),
                      "right": round((r.width - max_x) / 72, 2), "bottom": round(max(0, r.height - max_y) / 72, 2)}
    fp.fonts, fp.font_sizes, fp.colors = sorted(fonts), sorted(sizes), sorted(colors)
    fp.images, fp.profile_photo = images, profile
    return fp


def pdf_text(path: Path) -> str:
    doc = fitz.open(str(path))
    try:
        return "\n".join(page.get_text("text") for page in doc)
    finally:
        doc.close()


def pdf_page_count(path: Path) -> int:
    doc = fitz.open(str(path))
    try:
        return doc.page_count
    finally:
        doc.close()
