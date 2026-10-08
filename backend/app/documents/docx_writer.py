"""Write tailored content INTO the user's original DOCX (template preservation).

We never rebuild the document: the original file is reopened, the same paragraph enumeration
used during parsing locates each block, and only the text of changed paragraphs is replaced
(run formatting preserved). Everything else — styles, tables, images, profile photo, headers,
footers, section setup, numbering, hyperlinks — is carried over byte-for-byte by python-docx.
"""
from __future__ import annotations

from pathlib import Path

import docx

from ..core.jobs import UserFacingError
from ..core.models import ResumeSource
from ..parsing.docx_xml import W, enumerate_paragraphs, own_runs, paragraph_text, set_paragraph_text

MIN_SPACING_TWIPS = 40  # never squeeze paragraph spacing below 2pt


def write_tailored_docx(original: Path, resume: ResumeSource, texts: dict[str, str], out_path: Path,
                        spacing_factor: float = 1.0, collapse_empty: bool = False) -> dict:
    document = docx.Document(str(original))
    handles = enumerate_paragraphs(document)
    if len(handles) != len(resume.blocks):
        raise UserFacingError("The resume template could not be mapped reliably. Please re-upload the file.")
    changed = 0
    for block, handle in zip(resume.blocks, handles):
        current = paragraph_text(handle.element)
        if current != block.text:
            raise UserFacingError("The resume template could not be mapped reliably. Please re-upload the file.")
        new = texts.get(block.id, block.text)
        if new != block.text:
            set_paragraph_text(handle.element, new)
            changed += 1
    stats = {"paragraphs_changed": changed, "spacing_factor": spacing_factor, "empty_removed": 0}
    if spacing_factor < 1.0:
        _scale_spacing(document, spacing_factor)
    if collapse_empty:
        stats["empty_removed"] = _collapse_empty_paragraphs(document)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(out_path))
    return stats


def _scale_spacing(document, factor: float) -> None:
    roots = [document.element.body, document.styles.element]
    for root in roots:
        for sp in root.iter(W + "spacing"):
            if sp.getparent() is None or sp.getparent().tag != W + "pPr":
                continue
            for attr in ("before", "after"):
                v = sp.get(W + attr)
                if v and v.isdigit() and int(v) > MIN_SPACING_TWIPS:
                    sp.set(W + attr, str(max(MIN_SPACING_TWIPS, int(int(v) * factor))))


def _collapse_empty_paragraphs(document) -> int:
    """Remove runs of consecutive empty body paragraphs (keeps one), never ones holding drawings/breaks."""
    body = document.element.body
    removed = 0
    prev_empty = False
    for p in list(body.iterchildren(W + "p")):
        has_content = bool(paragraph_text(p).strip()) or p.find(f".//{W}drawing") is not None \
            or p.find(f".//{W}pict") is not None or p.find(f".//{W}sectPr") is not None \
            or any(r.find(W + "br") is not None for r in own_runs(p))
        if not has_content:
            if prev_empty:
                body.remove(p)
                removed += 1
                continue
            prev_empty = True
        else:
            prev_empty = False
    return removed


def docx_text(path: Path) -> str:
    document = docx.Document(str(path))
    return "\n".join(paragraph_text(h.element) for h in enumerate_paragraphs(document))
