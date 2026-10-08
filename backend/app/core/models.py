"""Core domain models shared across parsing, AI, tailoring, scoring and document generation."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

BlockKind = Literal["heading", "bullet", "paragraph", "empty"]
BlockLocation = Literal["body", "table", "textbox", "header", "footer"]


class BlockStyle(BaseModel):
    """Visual hints captured from the source (used to rebuild PDF-sourced resumes)."""

    font: Optional[str] = None
    size: Optional[float] = None
    bold: bool = False
    italic: bool = False
    color: Optional[str] = None  # hex RRGGBB
    align: Optional[str] = None  # left|center|right|justify
    page: Optional[int] = None
    x0: Optional[float] = None
    y0: Optional[float] = None
    space_before: Optional[float] = None


class Block(BaseModel):
    """One paragraph-level unit of the source resume. Every generated change targets a block."""

    id: str
    text: str
    kind: BlockKind = "paragraph"
    location: BlockLocation = "body"
    section: str = "header"  # normalized section key
    section_title: str = ""
    role: str = "other"
    editable: bool = False
    style: BlockStyle = Field(default_factory=BlockStyle)


class Contact(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None


class Section(BaseModel):
    key: str
    title: str
    block_ids: list[str] = Field(default_factory=list)


class Entry(BaseModel):
    """Experience / project / education entry, with references to its blocks."""

    entry_id: str
    title: str = ""
    organization: str = ""
    dates: str = ""
    location: str = ""
    header_block_ids: list[str] = Field(default_factory=list)
    bullet_block_ids: list[str] = Field(default_factory=list)

    @property
    def label(self) -> str:
        parts = [p for p in (self.title, self.organization) if p]
        return " — ".join(parts) if parts else self.entry_id


class SourceClaim(BaseModel):
    id: str  # SRC001
    claim: str
    block_ids: list[str] = Field(default_factory=list)
    evidence: str = ""  # verbatim quote from the source resume


class TemplateFingerprint(BaseModel):
    page_size: Optional[str] = None
    page_count: Optional[int] = None
    margins: dict[str, float] = Field(default_factory=dict)
    fonts: list[str] = Field(default_factory=list)
    font_sizes: list[float] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    sections: list[str] = Field(default_factory=list)
    section_breaks: int = 0
    tables: int = 0
    images: int = 0
    profile_photo: bool = False
    headers: int = 0
    footers: int = 0
    columns: int = 1
    text_boxes: int = 0
    hyperlinks: int = 0
    paragraphs: int = 0
    styles: list[str] = Field(default_factory=list)


class ResumeSource(BaseModel):
    """Source-of-truth model of the uploaded resume. Never populated from demo data."""

    resume_id: str
    source_hash: str
    filename: str
    file_type: Literal["docx", "pdf"]
    page_count: Optional[int] = None
    ocr_used: bool = False
    blocks: list[Block]
    name: str = ""
    headline: str = ""
    contact: Contact = Field(default_factory=Contact)
    sections: list[Section] = Field(default_factory=list)
    experience: list[Entry] = Field(default_factory=list)
    projects: list[Entry] = Field(default_factory=list)
    education: list[Entry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    claims: list[SourceClaim] = Field(default_factory=list)
    fingerprint: TemplateFingerprint = Field(default_factory=TemplateFingerprint)
    structuring: Literal["ai", "heuristic"] = "heuristic"
    warnings: list[str] = Field(default_factory=list)

    def block(self, block_id: str) -> Block | None:
        for b in self.blocks:
            if b.id == block_id:
                return b
        return None

    @property
    def full_text(self) -> str:
        return "\n".join(b.text for b in self.blocks if b.text.strip())

    def summary_counts(self) -> dict[str, Any]:
        return {
            "pages": self.page_count,
            "sections": len(self.sections),
            "experience_entries": len(self.experience),
            "skills": len(self.skills),
            "projects": len(self.projects),
            "education_entries": len(self.education),
            "certifications": len(self.certifications),
            "paragraphs": len([b for b in self.blocks if b.text.strip()]),
        }


KeywordCategory = Literal[
    "technical_skill", "tool", "framework", "programming_language", "cloud", "database",
    "methodology", "domain", "responsibility", "soft_skill", "education", "certification", "other",
]


class JDKeyword(BaseModel):
    term: str
    category: str = "other"
    importance: Literal["required", "preferred", "general"] = "general"


class JDAnalysis(BaseModel):
    job_title: str = ""
    company: str = ""
    years_experience: Optional[float] = None
    education_requirements: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    keywords: list[JDKeyword] = Field(default_factory=list)
    source: Literal["ai", "heuristic"] = "heuristic"


class KeywordEvidence(BaseModel):
    """Result of checking whether the source resume supports a JD keyword."""

    term: str
    category: str = "other"
    importance: str = "general"
    status: Literal["supported", "partial", "missing"] = "missing"
    match_type: Literal["exact", "alias", "related", "evidence", "partial_tokens", "none"] = "none"
    evidence: str = ""
    explanation: str = ""
    usable: bool = False  # may tailoring place this term in the resume?


ChangeStatus = Literal["suggested", "accepted", "rejected", "applied"]


class ChangeValidation(BaseModel):
    passed: bool = True
    issues: list[str] = Field(default_factory=list)


class Change(BaseModel):
    change_id: str
    block_id: str
    section: str
    section_title: str = ""
    entry_label: str = ""
    kind: Literal["rewrite", "reorder_skills"] = "rewrite"
    original: str
    suggested: str
    reason: str = ""
    source_claims: list[str] = Field(default_factory=list)
    source_evidence: list[str] = Field(default_factory=list)
    jd_keywords: list[str] = Field(default_factory=list)
    impact: Literal["high", "medium", "low"] = "low"
    status: ChangeStatus = "suggested"
    validation: ChangeValidation = Field(default_factory=ChangeValidation)
    pinned: bool = False  # kept across regenerations (user accepted it)
