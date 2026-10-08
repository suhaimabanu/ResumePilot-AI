"""Format-independent resume structuring.

Takes raw paragraphs (from DOCX or PDF parsing) and dynamically detects sections, roles,
editability, contact details and heuristic experience / project / education entries.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Optional

from ..core.models import Block, BlockStyle, Contact, Entry, Section

SECTION_ALIASES: dict[str, list[str]] = {
    "summary": ["summary", "professional summary", "profile", "professional profile", "about me", "about",
                "objective", "career objective", "career summary", "executive summary", "overview",
                "personal statement", "introduction", "summary of qualifications", "qualifications summary",
                "professional overview", "personal profile", "career profile", "profile summary"],
    "skills": ["skills", "technical skills", "core skills", "key skills", "core competencies", "competencies",
               "areas of expertise", "expertise", "technologies", "tech stack", "technical proficiencies",
               "skills tools", "tools", "tools technologies", "technical expertise", "skill set", "skillset",
               "skills summary", "it skills", "programming languages", "key competencies", "technical competencies",
               "skills abilities", "technical skills tools", "professional skills", "relevant skills", "soft skills",
               "hard skills", "skills expertise", "technical summary"],
    "experience": ["experience", "work experience", "professional experience", "employment", "employment history",
                   "work history", "career history", "relevant experience", "professional background",
                   "positions held", "internships", "internship experience", "internship", "experience summary",
                   "professional history", "industry experience", "work", "relevant work experience",
                   "teaching experience", "research experience", "freelance experience"],
    "projects": ["projects", "personal projects", "key projects", "selected projects", "academic projects",
                 "project experience", "notable projects", "side projects", "portfolio", "relevant projects",
                 "technical projects", "project highlights", "major projects"],
    "education": ["education", "academic background", "academic qualifications", "educational background",
                  "education training", "academics", "academic history", "educational qualifications",
                  "education qualifications", "academic credentials", "academic profile"],
    "certifications": ["certifications", "certificates", "certification", "licenses", "licenses certifications",
                       "certifications licenses", "professional certifications", "accreditations", "courses",
                       "training", "courses certifications", "certifications training", "professional development",
                       "trainings", "certifications courses", "relevant coursework", "coursework"],
    "achievements": ["achievements", "accomplishments", "key achievements", "highlights", "career highlights",
                     "key accomplishments", "notable achievements"],
    "awards": ["awards", "honors", "honours", "awards honors", "honors awards", "awards achievements",
               "recognition", "awards recognition", "scholarships"],
    "publications": ["publications", "research", "papers", "research publications", "patents", "presentations"],
    "languages": ["languages", "language skills", "spoken languages", "language proficiency", "language"],
    "volunteer": ["volunteer", "volunteering", "volunteer experience", "community service", "community involvement",
                  "extracurricular activities", "activities", "leadership", "leadership activities",
                  "extracurriculars", "volunteer work"],
    "affiliations": ["affiliations", "professional affiliations", "memberships", "professional memberships",
                     "associations"],
    "interests": ["interests", "hobbies", "hobbies interests", "personal interests", "interests hobbies"],
    "references": ["references", "referees", "reference"],
    "additional": ["additional information", "additional", "other", "miscellaneous", "personal details",
                   "personal information", "personal data", "other information", "declaration"],
    "contact": ["contact", "contact information", "contact details", "contact me", "get in touch"],
}

# Which sections may be rewritten and how their non-heading paragraphs are treated.
EDITABLE_SECTIONS = {"summary", "skills", "experience", "projects", "achievements", "volunteer"}
ENTRY_SECTIONS = {"experience", "projects", "education", "volunteer"}

MONTH = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?"
SINGLE_DATE = rf"(?:{MONTH}\s*,?\s*\d{{4}}|\d{{1,2}}\s*[/.-]\s*\d{{4}}|\d{{4}}\s*[/.-]\s*\d{{1,2}}|(?:19|20)\d{{2}})"
PRESENT = r"(?:present|current|now|today|ongoing|date)"
DATE_RANGE_RE = re.compile(rf"{SINGLE_DATE}\s*(?:[-–—~]|to|until|till)\s*(?:{SINGLE_DATE}|{PRESENT})", re.I)
DATE_ANY_RE = re.compile(rf"(?:{DATE_RANGE_RE.pattern})|{SINGLE_DATE}", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_RE = re.compile(r"(?<![\w/])(?:\+?\d[\d\s().-]{7,}\d)(?![\w/])")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:[\w-]+\.)?linkedin\.com/[^\s|,;]+", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[^\s|,;]+", re.I)
URL_RE = re.compile(r"(?:https?://|www\.)[^\s|,;]+|\b[\w-]+\.(?:com|io|dev|me|net|org|app|tech|site)(?:/[^\s|,;]*)?\b", re.I)
BULLET_CHARS = "•●▪■◦○◆◇►▸▹➢➤✓✔✗-–—*·⁃▪●◦•∙"
BULLET_PREFIX_RE = re.compile(rf"^\s*[{re.escape(BULLET_CHARS)}]\s+|^\s*[-]\s*")


def normalize_heading(text: str) -> str:
    t = text.lower().replace("&", " ").replace("/", " ")
    t = re.sub(r"[^a-z ]+", " ", t)
    t = re.sub(r"\band\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


_ALIAS_LOOKUP = {normalize_heading(a): key for key, aliases in SECTION_ALIASES.items() for a in aliases}


def match_section(text: str) -> Optional[str]:
    raw = text.strip().rstrip(":").strip()
    if not raw or len(raw) > 48 or len(raw.split()) > 6:
        return None
    if EMAIL_RE.search(raw) or DATE_ANY_RE.search(raw) or re.search(r"\d", raw):
        return None
    norm = normalize_heading(raw)
    if not norm:
        return None
    if norm in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[norm]
    close = difflib.get_close_matches(norm, list(_ALIAS_LOOKUP), n=1, cutoff=0.9)
    return _ALIAS_LOOKUP[close[0]] if close else None


def strip_bullet(text: str) -> tuple[str, str]:
    """Split a manual bullet prefix from text. Returns (prefix, rest)."""
    m = BULLET_PREFIX_RE.match(text)
    if not m:
        return "", text
    # "-" or "*" alone is only a bullet when followed by whitespace (handled by the regex)
    return text[: m.end()], text[m.end():]


@dataclass
class RawParagraph:
    text: str
    location: str = "body"
    is_list: bool = False
    is_heading_style: bool = False
    all_bold: bool = False
    all_caps: bool = False
    style: BlockStyle = field(default_factory=BlockStyle)


def _looks_like_name(text: str) -> bool:
    t = text.strip()
    if not t or len(t) > 60 or re.search(r"[\d@:/|]", t):
        return False
    words = t.replace(",", " ").split()
    if not 1 <= len(words) <= 5:
        return False
    if match_section(t):
        return False
    return all(re.match(r"^[A-Za-zÀ-ÿ'.\-]+$", w) for w in words) and any(w[0].isupper() for w in words)


def _is_contact_line(text: str) -> bool:
    return bool(EMAIL_RE.search(text) or LINKEDIN_RE.search(text) or GITHUB_RE.search(text)
                or (PHONE_RE.search(text) and not DATE_RANGE_RE.search(text)))


def extract_contact(lines: list[str]) -> Contact:
    contact = Contact()
    joined = "\n".join(lines)
    if m := EMAIL_RE.search(joined):
        contact.email = m.group(0)
    for m in PHONE_RE.finditer(joined):
        digits = re.sub(r"\D", "", m.group(0))
        if 8 <= len(digits) <= 15 and not DATE_RANGE_RE.search(m.group(0)):
            contact.phone = m.group(0).strip()
            break
    if m := LINKEDIN_RE.search(joined):
        contact.linkedin = m.group(0)
    if m := GITHUB_RE.search(joined):
        contact.github = m.group(0)
    for m in URL_RE.finditer(joined):
        url = m.group(0)
        if "linkedin" in url.lower() or "github" in url.lower() or (contact.email and url in contact.email):
            continue
        if "@" in joined[max(0, m.start() - 1): m.start() + 1]:
            continue
        contact.website = url
        break
    for line in lines:
        for piece in re.split(r"\s*[|•·;\t]\s*|\s{3,}", line):
            piece = piece.strip()
            if not piece or EMAIL_RE.search(piece) or URL_RE.search(piece) or PHONE_RE.search(piece):
                continue
            piece = re.sub(r"^(?:location|address)\s*:\s*", "", piece, flags=re.I)
            if re.match(r"^[A-Z][A-Za-zÀ-ÿ .'-]+,\s*[A-Z][A-Za-zÀ-ÿ .'-]+$", piece) and len(piece) < 50:
                contact.location = piece
                break
        if contact.location:
            break
    return contact


STRONG_SEP_RE = re.compile(r"\s*(?:\||•|·|–|—|\s-\s|\t)\s*")
WEAK_SEP_RE = re.compile(r"\s*(?:\s@\s|\bat\b|,)\s*")


def split_header(text: str) -> list[str]:
    cleaned = DATE_RANGE_RE.sub(" ", text)
    cleaned = re.sub(rf"\b{SINGLE_DATE}\b", " ", cleaned, flags=re.I)

    def keep(parts: list[str]) -> list[str]:
        out = []
        for p in parts:
            p = p.strip(" ()[],")
            if p and len(p) > 1 and not re.fullmatch(r"[\W\d]+", p):
                out.append(p)
        return out

    parts = keep(STRONG_SEP_RE.split(cleaned))
    if len(parts) <= 1:
        parts = keep(WEAK_SEP_RE.split(cleaned, maxsplit=1))
    return parts


def find_dates(text: str) -> str:
    if m := DATE_RANGE_RE.search(text):
        return m.group(0).strip()
    if m := DATE_ANY_RE.search(text):
        return m.group(0).strip()
    return ""


def split_skill_items(text: str) -> list[str]:
    body = text
    if ":" in body and body.index(":") < 40:
        body = body.split(":", 1)[1]
    _, body = strip_bullet(body)
    items, depth, cur = [], 0, ""
    for ch in body:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        if depth == 0 and ch in ",;|•·\t":
            items.append(cur)
            cur = ""
        else:
            cur += ch
    items.append(cur)
    items = [i.strip(" .") for i in items]
    return [i for i in items if i and len(i) <= 60 and len(i.split()) <= 6]


def classify(raw: list[RawParagraph]) -> tuple[list[Block], dict]:
    """Assign kinds, sections, roles and editability. Returns blocks and structural info."""
    blocks: list[Block] = []
    section_key = "header"
    section_title = ""
    seen_section = False
    seen_keys: set[str] = set()
    name_found = False
    headline_found = False

    for i, rp in enumerate(raw):
        text = rp.text.replace(" ", " ")
        stripped = text.strip()
        bid = f"B{i + 1:03d}"
        block = Block(id=bid, text=text, location=rp.location, style=rp.style)  # type: ignore[arg-type]
        if not stripped:
            block.kind = "empty"
            block.section, block.section_title = section_key, section_title
            blocks.append(block)
            continue
        if rp.location == "footer" or (rp.location == "header" and seen_section):
            # Page headers/footers are template furniture: never part of a section, never edited.
            block.kind, block.role = "paragraph", "page_" + rp.location
            block.section, block.section_title = "page_" + rp.location, ""
            blocks.append(block)
            continue

        sec = match_section(stripped)
        has_bullet = rp.is_list or bool(strip_bullet(text)[0])
        strong = rp.is_heading_style or rp.all_bold or rp.all_caps or stripped.endswith(":")
        exact_unseen = normalize_heading(stripped.rstrip(":")) in _ALIAS_LOOKUP and sec not in seen_keys
        heading_like = not has_bullet and (strong or exact_unseen)
        if sec and heading_like and not (sec == "contact" and _is_contact_line(stripped)):
            section_key, section_title, seen_section = sec, stripped.rstrip(":"), True
            seen_keys.add(sec)
            block.kind, block.role = "heading", "section_heading"
            block.section, block.section_title = sec, section_title
            blocks.append(block)
            continue
        if (not sec and rp.is_heading_style and seen_section and len(stripped.split()) <= 5
                and not DATE_ANY_RE.search(stripped) and not _is_contact_line(stripped)):
            # Unknown section using a heading style: keep it, but never edit it.
            section_key, section_title = "other", stripped.rstrip(":")
            block.kind, block.role = "heading", "section_heading"
            block.section, block.section_title = section_key, section_title
            blocks.append(block)
            continue

        prefix, rest = strip_bullet(text)
        block.kind = "bullet" if (rp.is_list or prefix) else "paragraph"
        block.section, block.section_title = section_key, section_title

        if section_key in ("header", "contact"):
            if _is_contact_line(stripped):
                block.role = "contact"
            elif not name_found and _looks_like_name(stripped):
                block.role, name_found = "name", True
            elif name_found and not headline_found and len(stripped) <= 90 and not DATE_ANY_RE.search(stripped):
                block.role, headline_found, block.editable = "headline", True, True
            elif len(stripped.split()) >= 12 and section_key == "header":
                # Unlabelled intro paragraph at the top acts as a summary.
                block.role, block.editable = "summary", True
            else:
                block.role = "contact" if section_key == "contact" else "header_other"
        elif section_key == "summary":
            block.role, block.editable = "summary", True
        elif section_key == "skills":
            block.role, block.editable = "skills", True
        elif section_key in ENTRY_SECTIONS:
            words = len(rest.split())
            is_header = block.kind != "bullet" and (words <= 14 or bool(DATE_ANY_RE.search(stripped))) and not stripped.endswith(".")
            prefix_role = {"experience": "experience", "projects": "project", "education": "education", "volunteer": "volunteer"}[section_key]
            if is_header:
                block.role = f"{prefix_role}_header"
            else:
                block.role = f"{prefix_role}_bullet"
                block.editable = section_key in EDITABLE_SECTIONS
        elif section_key == "achievements":
            block.role, block.editable = "achievement", True
        else:
            block.role = section_key
        blocks.append(block)

    info = build_structure(blocks)
    return blocks, info


def build_structure(blocks: list[Block]) -> dict:
    sections: list[Section] = []
    for b in blocks:
        if b.role == "section_heading":
            sections.append(Section(key=b.section, title=b.section_title, block_ids=[b.id]))
        elif sections and b.section == sections[-1].key and b.kind != "empty":
            sections[-1].block_ids.append(b.id)

    entries: dict[str, list[Entry]] = {"experience": [], "projects": [], "education": [], "volunteer": []}
    current: dict[str, Optional[Entry]] = {k: None for k in entries}
    counters = {k: 0 for k in entries}
    prefix_of = {"experience": "EXP", "projects": "PRJ", "education": "EDU", "volunteer": "VOL"}
    last_section = None
    for b in blocks:
        if b.section != last_section:
            last_section = b.section
            if b.section in current:
                current[b.section] = None
        if b.section not in entries or b.kind in ("empty", "heading"):
            continue
        key = b.section
        cur = current[key]
        header_text = b.text.strip()
        if b.role.endswith("_header"):
            starts_new = (
                cur is None
                or bool(cur.bullet_block_ids)
                or (cur.dates and DATE_ANY_RE.search(header_text) and len(cur.header_block_ids) >= 1)
                or len(cur.header_block_ids) >= 3
            )
            if starts_new:
                counters[key] += 1
                cur = Entry(entry_id=f"{prefix_of[key]}{counters[key]:02d}")
                entries[key].append(cur)
                current[key] = cur
            cur.header_block_ids.append(b.id)
            if not cur.dates:
                cur.dates = find_dates(header_text)
        else:
            if cur is None:
                counters[key] += 1
                cur = Entry(entry_id=f"{prefix_of[key]}{counters[key]:02d}")
                entries[key].append(cur)
                current[key] = cur
            cur.bullet_block_ids.append(b.id)

    by_id = {b.id: b for b in blocks}
    for key, lst in entries.items():
        for e in lst:
            parts: list[str] = []
            for hid in e.header_block_ids:
                parts.extend(split_header(by_id[hid].text))
            if key == "education":
                e.title = parts[0] if parts else ""
                e.organization = parts[1] if len(parts) > 1 else ""
            elif key == "projects":
                e.title = parts[0] if parts else ""
            else:
                e.title = parts[0] if parts else ""
                e.organization = parts[1] if len(parts) > 1 else ""

    name = next((b.text.strip() for b in blocks if b.role == "name"), "")
    headline = next((b.text.strip() for b in blocks if b.role == "headline"), "")
    contact_lines = [b.text for b in blocks if b.role in ("contact", "header_other", "name", "headline")]
    contact = extract_contact(contact_lines or [b.text for b in blocks[:15]])
    if not contact.email:
        contact = extract_contact([b.text for b in blocks])

    skills: list[str] = []
    for b in blocks:
        if b.section == "skills" and b.kind != "heading" and b.text.strip():
            for item in split_skill_items(b.text):
                if item.lower() not in {s.lower() for s in skills}:
                    skills.append(item)
    certifications = [strip_bullet(b.text)[1].strip() for b in blocks
                      if b.section == "certifications" and b.kind not in ("heading", "empty")]
    return {
        "sections": sections,
        "experience": entries["experience"],
        "projects": entries["projects"],
        "education": entries["education"],
        "volunteer": entries["volunteer"],
        "name": name,
        "headline": headline,
        "contact": contact,
        "skills": skills,
        "certifications": certifications,
    }
