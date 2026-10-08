"""Low-level DOCX helpers shared by the parser and the template-preserving writer.

The same enumeration function is used when parsing and when writing, so block IDs map to the
exact same <w:p> elements in the original document. Edits only touch text nodes inside existing
runs; styles, images, tables, headers/footers, section properties and relationships are untouched.
"""
from __future__ import annotations

import copy
import difflib
import re
from dataclasses import dataclass

from docx.document import Document as DocxDocument
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
V_NS = "urn:schemas-microsoft-com:vml"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
XML_NS = "http://www.w3.org/XML/1998/namespace"
W = f"{{{W_NS}}}"
NSMAP = {"w": W_NS, "mc": MC_NS, "a": A_NS, "v": V_NS, "wp": WP_NS}

TEXT_TAGS = {W + "t", W + "tab", W + "br", W + "cr", W + "noBreakHyphen", W + "softHyphen"}


@dataclass
class ParaHandle:
    element: etree._Element
    location: str  # body | table | textbox | header | footer
    part: str  # "document" or the part name


def _in_fallback(el: etree._Element) -> bool:
    return any(a.tag == f"{{{MC_NS}}}Fallback" for a in el.iterancestors())


def _location(el: etree._Element, default: str) -> str:
    tags = {a.tag for a in el.iterancestors()}
    if W + "txbxContent" in tags:
        return "textbox"
    if W + "tbl" in tags and default == "body":
        return "table"
    return default


def header_footer_parts(doc: DocxDocument) -> list[tuple[str, object]]:
    found: list[tuple[str, object]] = []
    seen: set[str] = set()
    for rel in doc.part.rels.values():
        if rel.reltype in (RT.HEADER, RT.FOOTER) and not rel.is_external:
            part = rel.target_part
            name = str(part.partname)
            if name in seen:
                continue
            seen.add(name)
            found.append(("header" if rel.reltype == RT.HEADER else "footer", part))
    found.sort(key=lambda x: (0 if x[0] == "header" else 1, str(x[1].partname)))
    return found


def enumerate_paragraphs(doc: DocxDocument) -> list[ParaHandle]:
    handles: list[ParaHandle] = []
    hf = header_footer_parts(doc)
    for kind, part in hf:
        if kind != "header":
            continue
        for p in part.element.iter(W + "p"):
            if not _in_fallback(p):
                handles.append(ParaHandle(p, "header", str(part.partname)))
    body = doc.element.body
    for p in body.iter(W + "p"):
        if not _in_fallback(p):
            handles.append(ParaHandle(p, _location(p, "body"), "document"))
    for kind, part in hf:
        if kind != "footer":
            continue
        for p in part.element.iter(W + "p"):
            if not _in_fallback(p):
                handles.append(ParaHandle(p, "footer", str(part.partname)))
    return handles


def own_runs(p: etree._Element) -> list[etree._Element]:
    """Runs whose nearest paragraph ancestor is `p` (excludes nested text-box paragraphs)."""
    runs = []
    for r in p.iter(W + "r"):
        between = []
        for a in r.iterancestors():
            if a.tag == W + "p":
                nearest = a
                break
            between.append(a.tag)
        else:
            continue
        if nearest is not p:
            continue
        if W + "del" in between or f"{{{MC_NS}}}Fallback" in between:
            continue
        runs.append(r)
    return runs


def run_text(r: etree._Element) -> str:
    out = []
    for child in r:
        tag = child.tag
        if tag == W + "t":
            out.append(child.text or "")
        elif tag == W + "tab":
            out.append("\t")
        elif tag in (W + "br", W + "cr"):
            out.append("\n")
        elif tag == W + "noBreakHyphen":
            out.append("‑")
    return "".join(out)


def paragraph_text(p: etree._Element) -> str:
    return "".join(run_text(r) for r in own_runs(p))


_TOKEN_RE = re.compile(r"\s+|\w+|[^\w\s]")


def _tokens(s: str) -> list[str]:
    return _TOKEN_RE.findall(s)


def _write_run_text(r: etree._Element, text: str) -> None:
    for child in list(r):
        if child.tag in TEXT_TAGS:
            r.remove(child)
    for piece in re.split(r"(\t|\n)", text):
        if piece == "":
            continue
        if piece == "\t":
            el = etree.SubElement(r, W + "tab")
        elif piece == "\n":
            el = etree.SubElement(r, W + "br")
        else:
            el = etree.SubElement(r, W + "t")
            el.text = piece
            el.set(f"{{{XML_NS}}}space", "preserve")


def set_paragraph_text(p: etree._Element, new_text: str) -> None:
    """Replace a paragraph's visible text while preserving run-level formatting.

    A token diff maps unchanged text back to its original run; inserted text inherits the
    formatting of the adjacent run. Runs are never re-created, so rPr, hyperlinks, fields and
    bookmarks stay where they were.
    """
    runs = own_runs(p)
    run_texts = [run_text(r) for r in runs]
    old = "".join(run_texts)
    if old == new_text:
        return
    if not runs:
        r = etree.SubElement(p, W + "r")
        ppr_rpr = p.find(f"{W}pPr/{W}rPr")
        if ppr_rpr is not None:
            rpr = copy.deepcopy(ppr_rpr)
            rpr.tag = W + "rPr"
            r.insert(0, rpr)
        _write_run_text(r, new_text)
        _mirror_fallback(p, new_text)
        return

    owner: list[int] = []
    for idx, t in enumerate(run_texts):
        owner.extend([idx] * len(t))
    text_runs = [i for i, t in enumerate(run_texts) if t]
    default_owner = text_runs[0] if text_runs else 0

    old_tok, new_tok = _tokens(old), _tokens(new_text)
    old_pos = [0]
    for t in old_tok:
        old_pos.append(old_pos[-1] + len(t))
    new_owner: list[int] = []
    sm = difflib.SequenceMatcher(None, old_tok, new_tok, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        new_chunk = "".join(new_tok[j1:j2])
        if op == "equal":
            new_owner.extend(owner[old_pos[i1]:old_pos[i2]])
        elif op == "replace":
            o = owner[old_pos[i1]] if old_pos[i1] < len(owner) else default_owner
            new_owner.extend([o] * len(new_chunk))
        elif op == "insert":
            start = old_pos[i1]
            if start == 0:
                o = owner[0] if owner else default_owner
            else:
                prev_char = old[start - 1]
                if start < len(owner) and (prev_char.isspace() or prev_char == ":"):
                    o = owner[start]
                else:
                    o = owner[start - 1]
            new_owner.extend([o] * len(new_chunk))
    # Keep the run order monotonic so text never moves out of sequence.
    running = 0
    for i, o in enumerate(new_owner):
        running = max(running, o)
        new_owner[i] = running

    buckets = [""] * len(runs)
    for ch, o in zip(new_text, new_owner):
        buckets[o] += ch
    for r, original_t, new_t in zip(runs, run_texts, buckets):
        if original_t != new_t:
            _write_run_text(r, new_t)
    _mirror_fallback(p, new_text)


def _mirror_fallback(p: etree._Element, new_text: str) -> None:
    """Text boxes are stored twice (DrawingML Choice + VML Fallback). Keep both in sync."""
    choice = next((a for a in p.iterancestors() if a.tag == f"{{{MC_NS}}}Choice"), None)
    if choice is None:
        return
    alt = choice.getparent()
    fallback = alt.find(f"{{{MC_NS}}}Fallback")
    if fallback is None:
        return
    choice_ps = list(choice.iter(W + "p"))
    fb_ps = list(fallback.iter(W + "p"))
    try:
        idx = choice_ps.index(p)
    except ValueError:
        return
    if idx < len(fb_ps) and len(fb_ps) == len(choice_ps):
        # Fallback paragraphs are excluded from enumeration, so recursion cannot loop.
        fb = fb_ps[idx]
        runs = own_runs(fb)
        if runs:
            set_paragraph_text(fb, new_text)


def iter_parts_xml(doc: DocxDocument):
    yield doc.element
    for _, part in header_footer_parts(doc):
        yield part.element


def count_not_in_fallback(root: etree._Element, xpath: str) -> int:
    return sum(1 for el in etree.XPath(xpath, namespaces=NSMAP)(root) if not _in_fallback(el))
