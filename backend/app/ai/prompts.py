"""Prompt templates. All factual content must come from the candidate's resume blocks."""
from __future__ import annotations

import json

from ..core.models import JDAnalysis, KeywordEvidence, ResumeSource, SourceClaim

SYSTEM_FACTUAL = (
    "You are a meticulous resume analyst. You only use facts explicitly present in the candidate's resume. "
    "A job description is never evidence that the candidate has a skill. You never invent technologies, "
    "employers, titles, dates, metrics, numbers, certifications, degrees, clients, responsibilities or years "
    "of experience. You always answer with a single JSON object that matches the requested schema."
)


def blocks_listing(resume: ResumeSource, only_text: bool = False) -> str:
    lines = []
    for b in resume.blocks:
        if not b.text.strip() or b.section.startswith("page_"):
            continue
        if only_text:
            lines.append(b.text.replace("\t", "  "))
        else:
            flag = "EDITABLE" if b.editable else "locked"
            lines.append(f"{b.id} [{b.section}/{b.role}/{flag}] {b.text.replace(chr(9), '  ')}")
    return "\n".join(lines)


def structure_prompt(resume: ResumeSource) -> str:
    return f"""Analyze the structure of this resume. Each line is one paragraph: ID [section/role/editability] text.

RESUME BLOCKS:
{blocks_listing(resume)}

Return JSON:
{{
  "experience": [{{"title": "", "company": "", "dates": "", "location": "", "header_blocks": ["B.."], "bullet_blocks": ["B.."]}}],
  "projects": [{{"name": "", "header_blocks": [], "bullet_blocks": []}}],
  "education": [{{"degree": "", "institution": "", "dates": "", "blocks": []}}],
  "certifications": [""],
  "skills": [""],
  "claims": [{{"claim": "short factual statement", "blocks": ["B.."], "quote": "exact verbatim words copied from those blocks"}}]
}}
Rules:
- Copy title, company, dates, degree, institution and certification names EXACTLY as written (verbatim substrings).
- Every experience entry in the resume must appear once, in the original order. Do not merge or drop entries.
- header_blocks are the lines holding title/company/dates; bullet_blocks are its description lines.
- Create 10-40 claims covering the candidate's skills, technologies, responsibilities and achievements.
  Each claim's "quote" must be copied verbatim from the referenced blocks.
- Use [] for absent sections. Never add information that is not in the blocks."""


def jd_prompt(jd_text: str, resume: ResumeSource) -> str:
    return f"""Analyze this job description, then check which of its keywords the candidate's resume genuinely supports.

JOB DESCRIPTION:
\"\"\"
{jd_text[:20000]}
\"\"\"

CANDIDATE RESUME (source of truth):
\"\"\"
{blocks_listing(resume, only_text=True)}
\"\"\"

Return JSON:
{{
  "job_title": "", "company": "", "years_experience": null,
  "education_requirements": [], "certifications": [],
  "required_skills": [], "preferred_skills": [], "responsibilities": [], "qualifications": [], "soft_skills": [],
  "keywords": [{{"term": "", "category": "technical_skill|tool|framework|programming_language|cloud|database|methodology|domain|responsibility|soft_skill|education|certification", "importance": "required|preferred|general"}}],
  "evidence": [{{"term": "", "quote": ""}}]
}}
Rules:
- keywords: 10-40 meaningful, specific terms that appear in the JD text (skills, tools, technologies, methodologies,
  domain terms, certifications). Use the JD's own wording. No generic filler words.
- years_experience: the minimum number of years required, or null.
- responsibilities: the duties listed in the JD, one per item, using its wording.
- evidence: ONLY for keywords the resume supports WITHOUT naming the keyword itself. "quote" must be copied
  verbatim from the resume (at least 3 words). If the resume does not clearly support a keyword, omit it.
  The JD is never evidence."""


def tailor_prompt(resume: ResumeSource, jd: JDAnalysis, evidence: list[KeywordEvidence], claims: list[SourceClaim],
                  locked_ids: set[str], style: str) -> str:
    usable = [e for e in evidence if e.usable]
    forbidden = [e.term for e in evidence if not e.usable]
    style_note = {
        "balanced": "Balance ATS keyword alignment with natural, concise wording.",
        "ats": "Prioritize placing supported JD keywords naturally (never stuffing).",
        "concise": "Make wording tighter and shorter than the original wherever possible.",
        "achievement": "Emphasize outcomes and achievements that are already stated in the resume.",
        "conservative": "CONSERVATIVE MODE overrides the depth above: make only small, high-value wording changes "
                        "(mainly JD terminology); keep most text as is.",
    }.get(style, "Balance ATS keyword alignment with natural, concise wording.")
    editable = [b for b in resume.blocks if b.editable and b.text.strip() and b.id not in locked_ids]
    entry_of: dict[str, str] = {}
    for e in resume.experience + resume.projects:
        for bid in e.bullet_block_ids:
            entry_of[bid] = e.label
    editable_lines = "\n".join(
        f"{b.id} [{b.section}{' / ' + entry_of[b.id] if b.id in entry_of else ''}] {b.text.replace(chr(9), '  ')}"
        for b in editable
    )
    claims_lines = "\n".join(f"{c.id}: {c.claim}" for c in claims[:120])
    return f"""Tailor this candidate's resume to the job description by rewriting the EDITABLE paragraphs so that a
recruiter for THIS role immediately sees the candidate's relevant experience. This is a real rewrite, not a proofread.

TARGET ROLE: {jd.job_title or 'see JD'}
JD REQUIRED SKILLS: {json.dumps(jd.required_skills[:25], ensure_ascii=False)}
JD RESPONSIBILITIES: {json.dumps(jd.responsibilities[:15], ensure_ascii=False)}

KEYWORDS THE RESUME SUPPORTS (you may use these where the paragraph's own facts support them):
{json.dumps([{"term": e.term, "evidence": e.evidence[:120]} for e in usable], ensure_ascii=False)}

KEYWORDS NOT EVIDENCED (NEVER add these or synonyms of them): {json.dumps(forbidden, ensure_ascii=False)}

SOURCE CLAIMS (facts from the resume):
{claims_lines}

FULL RESUME FOR CONTEXT:
{blocks_listing(resume)}

EDITABLE PARAGRAPHS (return every one of these IDs):
{editable_lines}

Return JSON:
{{"blocks": [{{"id": "B..", "text": "tailored text", "reason": "why this helps for this JD", "source_claims": ["SRC.."], "keywords": ["JD keywords addressed"]}}]}}

How to tailor (do all of these):
- Summary / profile paragraphs: ALWAYS rewrite. Position the candidate for the target role: open with their own
  professional identity from the resume, then foreground the experience, technologies and responsibilities from the
  resume that best match the JD, using the JD's wording where it is an accurate equivalent.
- Experience and project bullets: rewrite every bullet that relates to any JD skill or responsibility. Restructure it
  so the JD-relevant work and technologies come first, describe it in the JD's terminology (e.g. "RESTful services"
  -> "REST APIs", "worked with the product team" -> "collaborated with product managers"), and make the impact and
  scope from the original explicit. Prefer: strong action verb + task + technology/method + outcome.
- Bullets with no connection to the JD: improve the wording only; keep every fact in them.
- KEEP EVERYTHING: every fact, technology, tool, platform, responsibility, outcome and qualifier in the original
  paragraph must still be in your version (e.g. "ITIL-based production support", "for large-scale infrastructure
  automation", "improve scalability and performance"). Tailoring means rephrasing, reordering and re-emphasising —
  never removing. Rewrites are usually the same length or slightly longer, not shorter.
- Never add a seniority or rank (Senior, Lead, Principal, Staff, Head ...) that the resume does not state.
- Swapping a single word or reordering a list is NOT tailoring — a rewritten bullet should read noticeably different
  while saying only what the original says.

Hard rules (a violation gets the suggestion rejected):
- Return EVERY editable ID. Only return a paragraph unchanged if it truly has nothing to improve for this JD.
- Each paragraph must stay about the same subject and remain truthful to ITS OWN original facts. Do not move facts
  between jobs/projects.
- Never add numbers, percentages, metrics, dates, years of experience, employers, clients, tools or technologies that
  are not already in the resume. Keep every number that is in the original paragraph.
- Skill lines: you may only reorder the existing items (most JD-relevant first) and keep the same label text.
  Do not add or remove skills.
- Length: similar to the original (up to ~40% longer). Keep any leading bullet characters.
- No keyword stuffing; each keyword at most once per paragraph.
- No filler ("utilizing", "leveraging", "seamlessly", "robust", "successfully", "various") — use plain, specific verbs.
- {style_note}
- reason: one sentence naming the JD requirement this paragraph now addresses.
- source_claims: IDs of the claims that support the rewritten paragraph."""


def repair_prompt(items: list[dict], jd: JDAnalysis) -> str:
    return f"""Your tailored rewrites of these resume paragraphs were rejected by an automatic fact-checker.
Fix each one so it passes, while keeping as much of the tailoring for the target role ({jd.job_title or 'see JD'}) as
possible.

For each item: "original" is the candidate's text (the facts), "rejected" is your rewrite, "issues" says why it failed.
- "Adds X / Introduces X / not evidenced": remove X, or use the exact wording the original uses for that thing
  (e.g. original "troubleshot" -> write "troubleshot", not "troubleshooting").
- "Drops X": put X back.
- Numbers, dates, seniority: use only what the original says.

ITEMS:
{json.dumps(items, ensure_ascii=False, indent=1)}

Return JSON: {{"blocks": [{{"id": "B..", "text": "fixed tailored text", "reason": "why this helps for this JD",
"keywords": ["JD keywords addressed"]}}]}}"""


def condense_prompt(items: list[dict]) -> str:
    return f"""These resume paragraphs make the document overflow its original page count. Shorten each one
while keeping every fact, technology, number and keyword it contains. Do not add anything new.

PARAGRAPHS (target_chars is the maximum length):
{json.dumps(items, ensure_ascii=False, indent=1)}

Return JSON: {{"blocks": [{{"id": "B..", "text": "shortened text"}}]}}"""
