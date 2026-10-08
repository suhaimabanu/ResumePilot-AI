"""Render PDF pages to PNG images (preview + visual validation)."""
from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

PREVIEW_DPI = 110


def render_pages(pdf_path: Path, out_dir: Path, prefix: str, dpi: int = PREVIEW_DPI) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob(f"{prefix}_p*.png"):
        old.unlink(missing_ok=True)
    doc = fitz.open(str(pdf_path))
    paths = []
    try:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            path = out_dir / f"{prefix}_p{i + 1}.png"
            pix.save(str(path))
            paths.append(path)
    finally:
        doc.close()
    return paths


def page_signature(pdf_path: Path, size: tuple[int, int] = (85, 110)) -> list[list[int]]:
    """Low-resolution grayscale signature of each page for layout comparison."""
    doc = fitz.open(str(pdf_path))
    sigs = []
    try:
        for page in doc:
            zoom = size[0] / page.rect.width
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY, alpha=False)
            sigs.append(list(pix.samples))
    finally:
        doc.close()
    return sigs


def layout_similarity(sig_a: list[list[int]], sig_b: list[list[int]]) -> float | None:
    """0..1 similarity of rendered page layouts (ink distribution), compared page by page."""
    if not sig_a or not sig_b:
        return None
    sims = []
    for a, b in zip(sig_a, sig_b):
        n = min(len(a), len(b))
        if not n:
            continue
        # Compare ink presence in coarse rows to tolerate small wording changes.
        width = 85
        rows_a = [sum(1 for v in a[i:i + width] if v < 200) for i in range(0, n, width)]
        rows_b = [sum(1 for v in b[i:i + width] if v < 200) for i in range(0, n, width)]
        diff = sum(abs(x - y) for x, y in zip(rows_a, rows_b))
        total = sum(rows_a) + sum(rows_b) or 1
        sims.append(max(0.0, 1 - diff / total))
    if len(sig_a) != len(sig_b):
        sims.append(0.0)
    return round(sum(sims) / len(sims), 3) if sims else None
