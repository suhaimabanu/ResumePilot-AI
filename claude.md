Yes. Below is the **complete updated `CLAUDE.md`** with your original requirements plus the new real-world requirements:

 - Original uploaded template must be retained as closely as possible.
- Page count must be detected, preserved where possible, and displayed.
- One-click regenerate.
- Apply suggested changes selectively instead of forcing every change.
- Explainable ATS score.
- Before/after keyword coverage.
- DOCX/PDF visual and content validation.
- Full resume must always be based on the uploaded resume, not default/sample data.
- Tailoring must use all relevant JD keywords **only when supported by the original resume**.
- User control over AI suggestions.
- Stronger real-world validation and failure handling.

````
# Claude Code Master Prompt — AI Resume Tailor Web App

You are responsible for building a complete, working, end-to-end web application called **AI Resume Tailor**.

This is not a prototype, mockup, summary generator, or partial demo.

Build the actual application with a working frontend, backend, Gemini API integration, resume parsing, job-description parsing, AI resume analysis, complete resume tailoring, ATS analysis, source-fact validation, DOCX generation, PDF generation, original-template preservation, page-count handling, preview, selective user-controlled changes, downloads, visual validation, content validation, testing, and documentation.

The application must work with the **actual resume uploaded by the user**.

It must NEVER use default/sample resume data when a real resume has been uploaded.

---

# 1. MOST IMPORTANT REQUIREMENT

The application must allow a user to:

1. Upload their existing resume.
2. Upload or paste a Job Description.
3. Parse the actual uploaded resume.
4. Parse the actual supplied Job Description.
5. Analyze the actual resume against the actual JD.
6. Identify relevant JD keywords.
7. Determine which JD requirements are supported by the user's resume.
8. Tailor the **ENTIRE RESUME** according to the JD.
9. Preserve factual information from the original resume.
10. Preserve the user's original resume template/layout as closely as technically possible.
11. Preserve the original page structure and page count where technically possible.
12. Preserve the user's original formatting, sections, visual hierarchy, images, profile photo, tables, columns, fonts, colors, spacing, and other meaningful design elements.
13. Calculate a deterministic ATS compatibility score out of 100.
14. Explain exactly how the ATS score was calculated.
15. Show before/after ATS keyword coverage.
16. Show what changed.
17. Allow the user to selectively apply suggested changes.
18. Allow the user to regenerate the tailored resume with one click.
19. Generate the **COMPLETE tailored resume**, not just a summary.
20. Generate an actual DOCX file.
21. Generate an actual PDF file.
22. Validate the generated DOCX.
23. Validate the generated PDF.
24. Perform content validation.
25. Perform visual validation.
26. Display the actual completed tailored resume.
27. Display page count.
28. Allow the user to download DOCX/PDF.
29. Ensure the final exported documents correspond to the resume shown in the preview.

---

# 2. CRITICAL — THE UPLOADED RESUME IS THE SOURCE OF TRUTH

The uploaded resume is the primary source of truth.

The application must tailor **the user's actual resume**.

Do NOT use:

* sample resume data
* placeholder resume data
* default candidate data
* hardcoded names
* hardcoded experience
* hardcoded skills
* hardcoded projects
* demo content
* example companies
* fake achievements

unless the application is explicitly running in a separate demo/test mode.

When a real resume is uploaded:

```text
Uploaded Resume
      ↓
Parse Uploaded Resume
      ↓
Extract Actual Resume Data
      ↓
Create Source-of-Truth Resume Model
      ↓
Analyze Against Actual JD
      ↓
Tailor Actual Resume
      ↓
Validate Against Actual Resume
      ↓
Generate Actual Tailored Document
````

 The final resume must contain the user's actual:

 - name
- contact information
- professional title
- summary
- skills
- experience
- companies
- job titles
- dates
- projects
- education
- certifications
- achievements
- languages
- additional sections
- profile photo
- other meaningful content

 where present in the original resume.

---

 # 3\. DO NOT BUILD A SUMMARY-ONLY APPLICATION

 The application must NOT stop after generating:

 - a 2-line summary
- keywords
- recommendations
- suggested changes
- a few rewritten bullets

 The final output must be a **complete resume**.

 It must contain, wherever those sections exist in the original resume:

 - Name
- Contact information
- Professional headline/title
- Professional summary
- Technical skills
- Core competencies
- Work experience
- Company names
- Job titles
- Employment dates
- Responsibilities
- Achievements
- Projects
- Education
- Certifications
- Languages
- Additional sections
- Any other meaningful section present in the uploaded resume

 The final DOCX/PDF must contain the actual complete tailored resume.

---

 # 4\. REAL-WORLD USER CONTROL

 The AI must NOT silently make every possible change.

 Users must be able to review and control suggested changes.

 The application should distinguish between:

```
Recommended Changes
Applied Changes
Rejected Changes
Unchanged Content
```

 The user should have control over which suggested changes are applied.

---

 # 5\. "APPLY SUGGESTED CHANGES" FEATURE

 Do not force users to accept every AI recommendation.

 After analysis, show suggested changes individually.

 Example:

```
Suggested Changes

☑ Rewrite professional summary
☑ Reorder technical skills
☐ Rewrite Project A
☑ Improve experience bullet 1
☐ Add emphasis to AWS
```

 Each suggestion should show:

```
Section
Original
Suggested
Reason
Supporting Source Claims
JD Keywords Addressed
```

 Example:

```
Experience — Backend Developer

Before:
Developed backend applications.

Suggested:
Developed Python-based REST APIs supporting backend
application functionality and service integration.

Why:
Improves alignment with "Python", "REST APIs", and
"backend development" from the JD.

Source:
Original resume confirms Python and backend development.
```

 The user can:

```
Apply
Reject
```

 for individual suggestions.

 Also provide:

```
Apply All Suggested Changes
```

 and:

```
Reject All
```

 where appropriate.

---

 # 6\. IMPORTANT — AI MUST NOT FABRICATE INFORMATION

 The Job Description is not evidence that the candidate has a skill.

 For example, if the JD says:

```
Kubernetes
Terraform
AWS
Docker
```

 and the resume only proves:

```
AWS
Docker
```

 then:

```
AWS → can be emphasized
Docker → can be emphasized
Kubernetes → Missing / Not Evidenced
Terraform → Missing / Not Evidenced
```

 Never add Kubernetes or Terraform to the resume merely because they appear in the JD.

 Never invent:

 - technologies
- frameworks
- programming languages
- companies
- job titles
- responsibilities
- projects
- certifications
- degrees
- achievements
- metrics
- years of experience
- tools
- clients
- employers
- job duties

 If information is not supported by the source resume:

```
Do NOT add it to the final resume.
```

---

 # 7\. PROGRESS TRACKING — MANDATORY

 Create a root-level file:

```
progress.md
```

 This file is the **single source of truth for project progress, implementation status, completed work, pending work, decisions, changes, issues, and future modifications.**

 ## Claude MUST read `progress.md` before doing any implementation work.

 Before starting any task:

 1. Read `progress.md`.
2. Understand what has already been completed.
3. Identify the current phase.
4. Check pending tasks.
5. Check known issues.
6. Check requested changes.
7. Continue from the current state instead of rebuilding completed work.

 ## Claude MUST update `progress.md` after every meaningful implementation step.

 Update it whenever:

 - a feature is completed
- a file is created
- a major file is modified
- an API is implemented
- a frontend page is completed
- Gemini integration is completed
- resume parsing is implemented
- JD parsing is implemented
- resume tailoring is implemented
- ATS scoring is implemented
- DOCX generation is implemented
- PDF generation is implemented
- page-count handling is implemented
- template preservation is improved
- selective suggestions are implemented
- regeneration is implemented
- validation is implemented
- a bug is fixed
- a test is added
- a test fails
- a design decision is made
- a limitation is discovered
- a requirement changes
- the user requests a modification
- a feature is intentionally deferred

---

 # 8\. `progress.md` MUST CONTAIN

```
# AI Resume Tailor — Project Progress

## Current Status
- Overall completion:
- Current phase:
- Current task:
- Last updated:
- Application status:

## Completed
- [x] ...

## In Progress
- [ ] ...

## Pending
- [ ] ...

## Requested Changes
- [ ] ...

## Recently Completed Changes
- ...

## Files Created
- ...

## Files Modified
- ...

## Backend Status
- ...

## Frontend Status
- ...

## Gemini Integration Status
- ...

## Resume Parsing Status
- ...

## Job Description Parsing Status
- ...

## Resume Tailoring Status
- ...

## Source Claim Tracking Status
- ...

## Anti-Fabrication Validation Status
- ...

## Resume Completeness Validation Status
- ...

## ATS Scoring Status
- ...

## ATS Explainability Status
- ...

## Before/After Coverage Status
- ...

## Suggestion Review Status
- ...

## Regeneration Status
- ...

## DOCX Generation Status
- ...

## PDF Generation Status
- ...

## Template Preservation Status
- ...

## Page Count Status
- ...

## Visual Validation Status
- ...

## Content Validation Status
- ...

## Preview Status
- ...

## Download Status
- ...

## Testing Status
- ...

## Known Issues
- ...

## Decisions / Architecture Notes
- ...

## Next Recommended Step
- ...
```

---

 # 9\. USER CHANGE REQUESTS MUST ALSO USE `progress.md`

 The file:

```
progress.md
```

 must contain:

```
## Requested Changes
```

 If the user adds something there, Claude must read it and implement it.

 Example:

```
## Requested Changes

- [ ] Change the resume upload UI.
- [ ] Add PDF preview.
- [ ] Improve ATS score calculation.
- [ ] Preserve profile photo.
- [ ] Add DOCX + PDF download buttons.
- [ ] Preserve original template.
- [ ] Add page count.
- [ ] Add one-click regenerate.
- [ ] Add Apply Suggested Changes.
```

 Claude must:

 1. Read the requested changes.
2. Understand the request.
3. Implement the requested change.
4. Test it.
5. Mark it completed.
6. Record files changed.
7. Record implementation details.
8. Move unresolved items to pending/known issues.

---

 # 10\. DO NOT LOSE PREVIOUS WORK

 Before modifying anything:

 - Inspect the existing project.
- Read `progress.md`.
- Inspect relevant existing files.
- Understand the architecture.
- Do not unnecessarily rewrite working code.
- Do not delete completed functionality without a reason.
- Do not replace working functionality with simpler incomplete functionality.
- Preserve existing working features.

 If a requested change conflicts with an existing implementation:

 1. Document the conflict in `progress.md`.
2. Choose the safest implementation.
3. Preserve existing functionality.
4. Add regression tests.

---

 # 11\. PROJECT PHASE TRACKING

 Use phases similar to:

```
Phase 1 — Project Setup
Phase 2 — Frontend Foundation
Phase 3 — Resume Upload & Parsing
Phase 4 — Job Description Processing
Phase 5 — Gemini Integration
Phase 6 — Resume Analysis
Phase 7 — Full Resume Tailoring
Phase 8 — User-Controlled Suggested Changes
Phase 9 — Anti-Fabrication Validation
Phase 10 — Resume Completeness Validation
Phase 11 — ATS Scoring
Phase 12 — Explainable ATS + Before/After Coverage
Phase 13 — DOCX Template Preservation
Phase 14 — Page Count & Layout Preservation
Phase 15 — PDF Generation
Phase 16 — DOCX/PDF Content Validation
Phase 17 — DOCX/PDF Visual Validation
Phase 18 — Preview & Downloads
Phase 19 — One-Click Regeneration
Phase 20 — Testing
Phase 21 — UI/UX Refinement
Phase 22 — Final End-to-End Validation
```

 Clearly mark the current phase in `progress.md`.

---

 # 12\. FRONTEND REQUIREMENTS

 Build a modern AI-product interface inspired by the usability and simplicity of modern AI applications such as Claude, but DO NOT copy Claude's branding, logo, proprietary assets, or exact UI.

 Use an original design.

 Recommended visual direction:

 - clean light/off-white background
- dark charcoal text
- subtle purple/orange/pink accents
- tasteful gradients
- rounded cards
- modern typography
- spacious layout
- professional but friendly
- clear progress indicators
- drag-and-drop upload
- responsive design
- desktop/tablet/mobile support

 Recommended stack:

 - Next.js
- React
- TypeScript
- Tailwind CSS

---

 # 13\. MAIN USER WORKFLOW

 The home page should clearly guide the user through:

 ### Step 1 — Upload Resume

 Support:

 - DOCX
- PDF

 UI:

```
Upload Your Resume

Drag & drop your resume here
or
Browse Files

Supported: DOCX, PDF
```

 Display:

 - filename
- file type
- file size
- page count
- upload status
- remove/replace option

 After parsing, show:

```
Resume detected

5 pages
8 experience entries
12 skills
3 projects
2 certifications
```

 These values must come from the actual uploaded resume.

 Do NOT hardcode them.

---

 # 14\. RESUME PARSING

 The application must parse the actual uploaded resume.

 For DOCX:

 Extract:

 - paragraphs
- runs
- tables
- headers
- footers
- styles
- images
- hyperlinks
- page/section structure
- formatting information
- columns where possible

 For PDF:

 Extract:

 - text
- page boundaries
- sections
- positions where possible
- images
- page count
- layout information where possible

 For scanned PDFs:

 Use OCR where technically feasible.

 Create a normalized internal resume model.

 Example:

```
{
  "metadata": {
    "source_file": "",
    "file_type": "",
    "page_count": 0
  },
  "candidate": {
    "name": "",
    "contact": {}
  },
  "sections": [],
  "experience": [],
  "skills": [],
  "projects": [],
  "education": [],
  "certifications": [],
  "additional_sections": []
}
```

 The exact schema can be improved.

---

 # 15\. SOURCE-OF-TRUTH RESUME MODEL

 After parsing, create an internal structured representation of the actual uploaded resume.

 This model becomes the factual source of truth.

 For example:

```
ResumeSource
 ├── Candidate
 ├── Contact
 ├── Summary
 ├── Skills
 ├── Experience
 ├── Projects
 ├── Education
 ├── Certifications
 ├── Achievements
 └── Additional Sections
```

 Every generated change must be traceable to this source model.

---

 # 16\. SOURCE CLAIM TRACKING

 Create source claims from the original resume.

 Example:

```
SRC001 — Python backend development
SRC002 — REST API development
SRC003 — Django
SRC004 — FastAPI
SRC005 — Docker
SRC006 — AWS
```

 Generated content should reference source claims internally.

 Example:

```
{
  "bullet": "Developed REST APIs using Python and FastAPI...",
  "source_claims": ["SRC001", "SRC002", "SRC004"]
}
```

 Source claim IDs do not appear in the final resume.

---

 # 17\. JOB DESCRIPTION PROCESSING

 The application must parse the actual supplied JD.

 Support:

 - paste JD
- TXT
- PDF
- DOCX

 Extract:

 - job title
- required skills
- preferred skills
- technologies
- responsibilities
- qualifications
- education requirements
- certifications
- years of experience
- domain terminology
- soft skills
- keywords
- tools
- methodologies

 Separate:

```
Required
Preferred
Responsibilities
Keywords
Qualifications
```

---

 # 18\. KEYWORD EXTRACTION

 The system must identify all meaningful JD keywords.

 Do not blindly copy every word.

 Categorize keywords:

```
Technical Skills
Tools
Frameworks
Programming Languages
Cloud
Databases
Methodologies
Domain Terms
Responsibilities
Soft Skills
Education
Certifications
```

 Then determine:

```
Supported
Partially Supported
Missing / Not Evidenced
```

---

 # 19\. GEMINI API — USE GEMINI, NOT OLLAMA

 Do NOT use Ollama.

 Use Google's Gemini API.

 Recommended SDK:

```
pip install -U google-genai
```

 Use:

```
from google import genai
```

 Configuration:

```
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=your_configured_model
```

 Never expose the API key to the frontend.

 Never hardcode the key.

 Use environment variables.

 Keep Gemini behind a backend service abstraction.

 Recommended:

```
backend/
  app/
    services/
      ai/
        base.py
        gemini.py
        prompts.py
```

 Example:

```
class AIProvider:
    ...
```

 and:

```
class GeminiProvider(AIProvider):
    ...
```

---

 # 20\. GEMINI MUST TAILOR THE COMPLETE RESUME

 Gemini must not only generate:

```
summary
keywords
recommendations
```

 It must generate structured content representing the complete tailored resume.

 Example:

```
{
  "resume": {
    "name": "",
    "headline": "",
    "contact": {},
    "summary": "",
    "skills": [],
    "experience": [],
    "projects": [],
    "education": [],
    "certifications": [],
    "achievements": [],
    "additional_sections": []
  },
  "analysis": {
    "matched_keywords": [],
    "partial_matches": [],
    "missing_keywords": [],
    "changes": []
  }
}
```

 Every rewritten item should contain source references where possible.

---

 # 21\. TAILORING STRATEGY

 Tailoring should optimize for the JD without changing the candidate's factual identity.

 The AI should primarily:

 - improve wording
- reorder relevant skills
- emphasize relevant experience
- improve keyword alignment
- rewrite bullets using existing facts
- improve summary
- improve project descriptions
- align terminology with the JD where factually supported
- prioritize relevant accomplishments
- reduce irrelevant emphasis where appropriate
- preserve factual content

 Do NOT rewrite the resume as if the candidate has experience they do not have.

---

 # 22\. COMPLETE RESUME PRESERVATION

 If the original resume contains:

```
5 experience entries
```

 the generated resume should contain:

```
5 experience entries
```

 unless the user explicitly removes an entry.

 If the original contains:

```
3 projects
```

 the generated resume should retain those projects unless the user explicitly removes them.

 The AI may reorder or refine content, but it must not silently delete meaningful source content.

---

 # 23\. USER-CONTROLLED CHANGE MODEL

 Every suggested modification should have an ID.

 Example:

```
{
  "change_id": "CHG001",
  "section": "summary",
  "status": "suggested",
  "original": "...",
  "suggested": "...",
  "reason": "...",
  "source_claims": ["SRC001", "SRC002"],
  "jd_keywords": ["Python", "REST API"]
}
```

 Possible statuses:

```
suggested
accepted
rejected
applied
```

 The user must be able to modify the selection before final generation.

---

 # 24\. APPLY SUGGESTED CHANGES

 Provide:

```
Apply Suggested Changes
```

 The user should be able to:

```
Apply All
```

 or selectively:

```
☑ Change Summary
☐ Change Experience #1
☑ Reorder Skills
☐ Change Project #2
```

 The final resume must be generated using the user's selected changes.

---

 # 25\. ONE-CLICK REGENERATE

 Add a prominent:

```
Regenerate Resume
```

 button.

 One-click regeneration must:

 1. Use the same uploaded resume.
2. Use the same JD.
3. Preserve accepted/rejected changes.
4. Re-run tailoring.
5. Re-run validation.
6. Recalculate ATS.
7. Regenerate DOCX.
8. Regenerate PDF.
9. Re-run visual/content validation.
10. Update the preview.
11. Update page count.
12. Update before/after coverage.

 Do not reset user selections unless explicitly requested.

 The user should be able to regenerate without uploading everything again.

---

 # 26\. REGENERATION OPTIONS

 Support:

```
Regenerate
Regenerate with Current Selections
Start Over
```

 Potential future options:

```
More ATS-focused
More concise
More achievement-focused
More conservative
```

 Do not introduce unsupported facts during regeneration.

---

 # 27\. PROCESSING SCREEN

 Show real progress.

 Example:

```
Analyzing your resume...

✓ Reading Resume
✓ Understanding Job Description
✓ Matching Skills
✓ Creating Tailoring Suggestions
✓ Applying Selected Changes
✓ Fact Checking
✓ Resume Completeness Check
✓ ATS Analysis
○ Creating DOCX
○ Creating PDF
○ Visual Validation
○ Final Validation
```

 Do not fake progress.

 The frontend must receive real backend job status.

---

 # 28\. ASYNC JOB PROCESSING

 Resume generation may take time.

 Use job-based processing.

 Example:

```
POST /api/resume/tailor
```

 returns:

```
{
  "job_id": "..."
}
```

 Frontend polls:

```
GET /api/jobs/{job_id}/status
```

 Backend returns:

```
{
  "status": "processing",
  "step": "Creating DOCX",
  "progress": 82
}
```

 When complete:

```
{
  "status": "completed",
  "progress": 100,
  "docx_url": "...",
  "pdf_url": "...",
  "ats_score": 87,
  "page_count": 2
}
```

---

 # 29\. IMPORTANT — REAL PROGRESS ONLY

 Do not show:

```
100%
```

 unless the entire workflow is actually complete.

 Do not fake:

 - document creation
- PDF generation
- validation
- downloads
- ATS analysis
- page count
- preview generation

---

 # 30\. FINAL RESULT PAGE

 After successful processing:

```
Your Tailored Resume is Ready

ATS Compatibility Score
87 / 100

Original Score
74 / 100

Improvement
+13

Pages
2
```

 Show:

```
[ Download DOCX ]

[ Download PDF ]

[ Download Both ]

[ Regenerate ]
```

 These must be real working buttons.

 Do NOT make buttons that merely display filenames.

---

 # 31\. PAGE COUNT — MANDATORY

 Page count must be calculated from the actual generated document.

 Display:

```
Original Resume
3 pages

Tailored Resume
2 pages
```

 or:

```
Tailored Resume
2 pages
```

 depending on the UI context.

 Do NOT hardcode page counts.

 Page count must be derived from:

 - actual PDF page count
- actual DOCX rendered page count where feasible

 The PDF should be treated as the authoritative page-count source when DOCX is converted to PDF.

---

 # 32\. PAGE COUNT VALIDATION

 The backend must verify:

```
PDF page count
```

 and compare it with expected output.

 If the user requested preservation of page count:

```
Original: 2 pages
Target: 2 pages
Generated: 2 pages
```

 If the tailored content causes unavoidable expansion:

```
Original: 2 pages
Generated: 3 pages
```

 The system should detect this and attempt layout optimization before accepting the result.

 Do not reduce font size or spacing to unreadable levels merely to force a page count.

---

 # 33\. PAGE-LENGTH OPTIMIZATION

 When tailoring causes page overflow:

 1. Detect overflow.
2. Attempt content-aware optimization.
3. Remove unnecessary repetition.
4. Reduce excessive spacing.
5. Rebalance sections.
6. Preserve original design.
7. Preserve readability.
8. Re-render.
9. Recalculate page count.
10. Validate again.

 Never:

 - remove factual experience
- remove important sections
- delete achievements
- fabricate concise metrics
- shrink text to an unreadable size

---

 # 34\. COMPLETE RESUME PREVIEW

 The result page must show the **full tailored resume**.

 Do not only show:

 - summary
- score
- keywords

 Preferably render the actual generated PDF/document.

 The preview must correspond to the actual exported document.

 Show:

```
Page 1 / 2
Page 2 / 2
```

 where applicable.

 The preview must update after regeneration.

---

 # 35\. ORIGINAL TEMPLATE MUST BE RETAINED

 This is a critical requirement.

 If the user uploads a DOCX resume, use that actual DOCX as the template.

 Do NOT:

```
extract text
→ generate new resume
→ create generic DOCX
```

 Instead:

```
Original Uploaded Resume
        ↓
Inspect Original Structure
        ↓
Identify Editable Content
        ↓
Tailor Content
        ↓
Replace Content in Original Structure
        ↓
Preserve Formatting
        ↓
Render
        ↓
Validate
```

 The final document should visually resemble the uploaded resume as closely as technically possible.

---

 # 36\. TEMPLATE PRESERVATION DETAILS

 Inspect and preserve:

 - paragraphs
- runs
- tables
- headers
- footers
- images
- profile photo
- styles
- fonts
- font sizes
- font weights
- font colors
- background colors
- margins
- spacing
- line spacing
- alignment
- bullets
- numbering
- hyperlinks
- icons/images
- columns
- page size
- section breaks
- section ordering
- tables
- text boxes where technically possible

 Goal:

```
Original Resume Template
        +
Tailored Content
        =
Original Design + Tailored Content
```

---

 # 37\. TEMPLATE FINGERPRINT

 Create a template representation before modification.

 Example:

```
{
  "page_size": "...",
  "margins": {},
  "fonts": [],
  "colors": [],
  "sections": [],
  "tables": 0,
  "images": 0,
  "headers": 0,
  "footers": 0,
  "columns": 0
}
```

 After generation, compare the original and generated template fingerprints.

 Report:

```
Template Preservation

Fonts: Preserved
Margins: Preserved
Sections: Preserved
Profile Photo: Preserved
Tables: Preserved
Columns: Preserved
Colors: Preserved
```

 If something cannot be preserved:

```
Template limitation detected:
Text box positioning could not be preserved exactly.
```

 Do not silently replace the design.

---

 # 38\. DOCX GENERATION

 DOCX generation is a core feature.

 Use an appropriate Python DOCX library such as:

```
python-docx
```

 The implementation must work with real uploaded documents.

 Do not create a dummy DOCX.

 The generated DOCX must contain:

 - complete tailored resume
- actual user information
- actual experience
- actual skills
- actual education
- actual projects
- actual certifications
- selected AI changes
- original template wherever possible

---

 # 39\. DOCX TEMPLATE EDITING

 When editing a DOCX:

 Prefer modifying the existing document rather than rebuilding it.

 Preserve:

 - existing styles
- runs
- tables
- images
- headers
- footers
- section breaks
- page setup
- paragraph formatting

 Where text needs replacement, preserve the formatting of the existing run/paragraph where possible.

 Do not destroy document relationships unnecessarily.

---

 # 40\. PROFILE PHOTO PRESERVATION

 If the original resume contains a profile photo:

 1. Detect it.
2. Preserve it.
3. Keep its approximate location.
4. Keep dimensions/aspect ratio where possible.
5. Validate that the generated DOCX still contains it.
6. Validate that the generated PDF still displays it.

 If preservation fails:

 - record the issue in `progress.md`
- attempt an alternative implementation
- never silently discard it

---

 # 41\. PDF GENERATION

 Prefer generating PDF from the final DOCX using LibreOffice headless or another reliable document conversion method.

 Example:

```
libreoffice --headless --convert-to pdf ...
```

 This helps keep DOCX and PDF visually consistent.

 Validate:

 - PDF exists
- PDF opens
- PDF contains complete resume
- PDF is not blank
- PDF is not only a summary
- page count is correct
- text is readable
- images render
- layout is intact

---

 # 42\. PDF INPUT

 If the original resume is PDF:

 - extract text and structure
- identify sections
- preserve content
- preserve page structure
- preserve layout where technically possible
- preserve images where possible
- preserve page count where possible
- OCR scanned PDFs when feasible

 If exact template preservation cannot be achieved for a particular PDF:

 - explain the limitation
- preserve content
- preserve structure/layout as closely as technically possible

 Recommend DOCX as the preferred input when maximum template preservation is required.

---

 # 43\. VISUAL VALIDATION — MANDATORY

 The final DOCX/PDF must undergo visual validation.

 Do not assume that because a file was generated successfully it looks correct.

 The backend should render the final PDF pages to images where technically feasible.

 Check for:

 - blank pages
- overlapping text
- clipped text
- cut-off content
- broken columns
- broken tables
- missing profile photo
- missing icons
- incorrect fonts
- inconsistent spacing
- orphaned headings
- excessive whitespace
- content outside page boundaries
- unreadably small text
- unexpected page overflow

 The visual validation stage should produce a validation result.

 Example:

```
{
  "visual_validation": {
    "passed": true,
    "pages_checked": 2,
    "issues": []
  }
}
```

 If issues are detected:

```
DO NOT immediately mark the document complete.

Attempt correction and re-render.
```

---

 # 44\. DOCX CONTENT VALIDATION — MANDATORY

 After DOCX generation, reopen the generated DOCX and extract its text.

 Compare against the expected tailored resume.

 Validate:

 - candidate name
- contact information
- headline
- summary
- skills
- companies
- job titles
- dates
- experience entries
- projects
- education
- certifications
- achievements
- additional sections

 The generated DOCX must contain the complete resume.

---

 # 45\. PDF CONTENT VALIDATION — MANDATORY

 Extract text from the generated PDF.

 Compare against the expected final resume.

 Validate:

```
Expected Resume Content
        ↓
Generated PDF Text
        ↓
Content Comparison
```

 Detect:

 - missing sections
- missing experience
- missing company names
- missing dates
- missing skills
- truncated output
- blank pages
- unexpectedly short output

 If important content is missing:

```
FAIL VALIDATION
```

 and attempt regeneration/correction.

---

 # 46\. DOCX/PDF CONSISTENCY VALIDATION

 The DOCX and PDF should represent the same final resume.

 Compare:

```
DOCX extracted content
vs
PDF extracted content
```

 Allow reasonable formatting differences.

 Detect:

 - missing text
- missing sections
- missing pages
- missing images
- major layout inconsistencies

 Example:

```
DOCX:
2 pages
Complete resume

PDF:
2 pages
Complete resume

Status:
PASS
```

---

 # 47\. FINAL DOCUMENT VALIDATION PIPELINE

 Before allowing downloads:

```
Tailored Resume
      ↓
Source Fact Validation
      ↓
Completeness Validation
      ↓
DOCX Generation
      ↓
DOCX Content Validation
      ↓
PDF Generation
      ↓
PDF Content Validation
      ↓
DOCX/PDF Consistency Validation
      ↓
Visual Validation
      ↓
Page Count Validation
      ↓
Final Validation
      ↓
Allow Downloads
```

 Downloads must not be enabled if critical validation fails.

---

 # 48\. RESUME COMPLETENESS VALIDATION

 Create:

```
resume_completeness_validator.py
```

 Check:

 - name exists
- contact exists
- summary exists if original has one
- skills exist
- every original experience entry exists
- every company exists
- every job title exists
- every employment date exists
- each experience has meaningful bullets
- projects are preserved where present
- education is preserved
- certifications are preserved
- additional sections are preserved
- output is not suspiciously short
- output is not only a summary

 Example:

```
Source:
5 experience entries

Generated:
5 experience entries

Result:
PASS
```

 If:

```
Source:
5 experience entries

Generated:
2 experience entries
```

 then:

```
FAIL
```

 Do not export.

---

 # 49\. PREVENT TRUNCATED AI OUTPUT

 Do not blindly trust Gemini.

 If Gemini returns an incomplete resume:

```
DO NOT EXPORT IT.
```

 Instead:

 1. Detect incomplete output.
2. Retry Gemini if appropriate.
3. Merge missing sections from the source resume.
4. Validate again.
5. Only export after completeness validation passes.

---

 # 50\. ATS SCORING

 Do NOT allow Gemini to arbitrarily decide the final ATS score.

 Implement deterministic ATS scoring in Python.

 Recommended weighting:

```
Keyword Match                 30
Required Skills               20
Experience Alignment          15
Responsibilities Alignment    15
Education/Certifications      10
Formatting/Parsing             10
--------------------------------
TOTAL                         100
```

 Call it:

```
ATS Compatibility Score
```

 Do not call it:

```
Official ATS Score
```

 because different ATS systems calculate scores differently.

---

 # 51\. EXPLAINABLE ATS SCORE — MANDATORY

 The ATS score must be explainable.

 Do not simply show:

```
87 / 100
```

 Show how the score was calculated.

 Example:

```
ATS Compatibility
87 / 100

Keyword Match
26 / 30

Required Skills
17 / 20

Experience Alignment
14 / 15

Responsibilities Alignment
13 / 15

Education / Certifications
9 / 10

Formatting / Parsing
8 / 10
```

 Allow the user to expand each category.

 For example:

```
Keyword Match — 26/30

Matched:
Python
REST API
FastAPI
Docker
AWS

Partial:
Microservices

Missing:
Kubernetes
Terraform
```

---

 # 52\. BEFORE / AFTER ATS COVERAGE

 Show ATS coverage before and after tailoring.

 Example:

```
JD Keyword Coverage

Original Resume
72%

Tailored Resume
91%

Improvement
+19%
```

 Also show:

```
Matched Before: 18 / 25
Matched After: 23 / 25
```

 The system must calculate these values deterministically.

 Do not ask Gemini to invent the percentage.

---

 # 53\. ATS KEYWORD MATCHING

 Support:

 - exact matching
- normalized matching
- aliases
- terminology variations
- semantic matching where appropriate

 Examples:

```
REST API ≈ RESTful API
PostgreSQL ≈ Postgres
Amazon Web Services ≈ AWS
```

 Do NOT treat unrelated technologies as equivalent.

 Example:

```
Django ≠ React
Python ≠ Java
AWS ≠ Azure
```

 unless there is a clearly defined, defensible equivalence.

---

 # 54\. ATS ANALYSIS OUTPUT

 Show:

 ### Matched Keywords

```
Python
REST API
FastAPI
Docker
AWS
```

 ### Partial Matches

```
Cloud deployment
Microservices
CI/CD
```

 ### Missing / Not Evidenced

```
Kubernetes
Terraform
```

 Never add missing skills to the resume.

---

 # 55\. ATS SCORE COMPARISON

 Show:

```
Original Resume
74 / 100

Tailored Resume
87 / 100

Improvement
+13
```

 Also show:

```
Keyword Coverage
Original: 72%
Tailored: 91%

Required Skill Coverage
Original: 70%
Tailored: 90%
```

---

 # 56\. ATS SCORE MUST NOT ENCOURAGE KEYWORD STUFFING

 Do not repeat keywords unnaturally.

 The goal is:

```
Relevant keyword alignment
+
Natural language
+
Factual accuracy
```

 Not:

```
Keyword stuffing
```

 Penalize unnatural repetition where appropriate.

---

 # 57\. "WHAT CHANGED?" SECTION

 Show useful before/after information.

 Example:

```
What Changed?

Professional Summary

Before:
Python developer with backend experience...

After:
Python backend engineer experienced in REST APIs,
microservices and automation...

Reason:
Improves alignment with the JD.

Supported by:
Python
Backend development
REST APIs
```

 Only show changes supported by the original resume.

---

 # 58\. CHANGE IMPACT

 Each suggested change should indicate:

```
ATS Impact
High / Medium / Low
```

 Example:

```
Rewrite Summary
ATS Impact: High

Reorder Skills
ATS Impact: Medium

Rewrite Project 2
ATS Impact: Low
```

 This helps users make informed decisions.

---

 # 59\. USER REVIEW BEFORE FINAL GENERATION

 Where appropriate, the workflow should be:

```
Analyze
 ↓
Show Suggested Changes
 ↓
User Reviews
 ↓
Apply Selected Changes
 ↓
Generate Final Resume
```

 Do not force the AI-generated version immediately if the user wants control.

 Provide a convenient:

```
Generate With My Selections
```

 button.

---

 # 60\. ONE-CLICK REGENERATE AFTER EDITS

 If the user changes selections:

```
Apply / Reject Changes
        ↓
Regenerate
        ↓
Validate
        ↓
ATS Recalculation
        ↓
DOCX
        ↓
PDF
        ↓
Preview
```

 The entire process must use the actual current resume state.

---

 # 61\. API DESIGN

 Implement appropriate backend APIs, such as:

```
POST /api/resume/upload
POST /api/jd/analyze
POST /api/resume/analyze
POST /api/resume/suggestions
POST /api/resume/apply-changes
POST /api/resume/tailor
POST /api/resume/regenerate
POST /api/resume/validate
POST /api/resume/score
POST /api/resume/export

GET /api/jobs/{job_id}/status

GET /api/download/{file_id}

GET /api/health
```

 You may improve the API architecture.

---

 # 62\. JOB STATUS MODEL

 The job should contain real states such as:

```
queued
parsing_resume
parsing_jd
analyzing
generating_suggestions
waiting_for_user
applying_changes
validating
scoring
generating_docx
generating_pdf
visual_validation
final_validation
completed
failed
```

 Do not use fake status values.

---

 # 63\. PRIVACY

 Resume files contain sensitive personal information.

 Implement sensible privacy practices.

 At minimum:

 - do not expose files publicly
- do not expose Gemini API key
- validate file types
- validate file sizes
- avoid unnecessary permanent storage
- clean temporary files where possible
- do not log full resumes unnecessarily
- do not log API keys
- do not expose internal errors to users
- use secure file identifiers
- prevent path traversal
- restrict file access

---

 # 64\. FILE VALIDATION

 Validate:

 - extension
- MIME type
- file signature where possible
- file size
- document integrity

 Supported resume formats:

```
.docx
.pdf
```

 Supported JD formats:

```
.txt
.docx
.pdf
```

 Reject:

 - executable files
- scripts
- unsupported archives
- malicious files
- corrupted documents

---

 # 65\. ERROR HANDLING

 Handle:

 - invalid file
- unsupported file type
- oversized file
- corrupt DOCX
- corrupt PDF
- scanned PDF
- OCR failure
- Gemini API failure
- Gemini timeout
- malformed Gemini response
- incomplete AI response
- source validation failure
- DOCX generation failure
- PDF generation failure
- LibreOffice unavailable
- visual validation failure
- content validation failure
- page overflow
- download failure

 Frontend errors should be human-readable.

 Do not expose stack traces or internal implementation details to users.

---

 # 66\. TESTING

 Create tests for:

 ### Upload

 - DOCX upload
- PDF upload
- invalid file
- oversized file
- corrupt file

 ### Parsing

 - resume extraction
- JD extraction
- page count
- DOCX structure
- PDF structure
- OCR fallback

 ### Source Truth

 - source claim creation
- source claim mapping
- factual validation

 ### Gemini

 - API integration
- structured response parsing
- malformed response
- retry handling
- incomplete response

 ### Tailoring

 - full resume generation
- actual uploaded resume usage
- experience preservation
- company preservation
- date preservation
- anti-fabrication
- completeness validation
- suggested changes
- selective application
- regeneration

 ### ATS

 - keyword matching
- aliases
- normalization
- semantic matching
- score calculation
- original vs tailored score
- explainable scoring
- before/after coverage

 ### Documents

 - DOCX generation
- template preservation
- profile photo preservation
- page count
- PDF generation
- PDF validity
- DOCX content validation
- PDF content validation
- DOCX/PDF consistency
- visual validation
- page overflow

 ### Preview

 - full resume preview
- multiple pages
- correct page count
- preview matches exported PDF

 ### Downloads

 - DOCX download
- PDF download
- both download
- invalid/expired download handling

 ### End-to-End

 Test:

```
Upload Resume
      ↓
Parse Actual Resume
      ↓
Upload/Paste JD
      ↓
Analyze Actual Resume vs Actual JD
      ↓
Generate Suggestions
      ↓
User Selects Changes
      ↓
Apply Selected Changes
      ↓
Tailor COMPLETE Resume
      ↓
Validate Facts
      ↓
Validate Completeness
      ↓
Calculate Original ATS
      ↓
Calculate Tailored ATS
      ↓
Generate DOCX
      ↓
Generate PDF
      ↓
Validate DOCX
      ↓
Validate PDF
      ↓
Validate Visual Layout
      ↓
Validate Page Count
      ↓
Show Full Preview
      ↓
Download DOCX/PDF
```

---

 # 67\. FINAL END-TO-END ACCEPTANCE TEST

 Do not consider the application complete until this works using a real resume.

 Use:

```
Real uploaded resume
+
Real job description
```

 Expected:

```
Resume uploaded
↓
Actual resume parsed
↓
Actual resume data extracted
↓
JD parsed
↓
Keywords extracted
↓
Resume/JD analyzed
↓
Suggestions generated
↓
User can accept/reject suggestions
↓
Complete tailored resume generated
↓
All original experience entries preserved
↓
Original companies preserved
↓
Original titles preserved
↓
Original dates preserved
↓
No unsupported skills added
↓
ATS score calculated
↓
ATS score explained
↓
Before/after keyword coverage shown
↓
Original template preserved
↓
Page count calculated
↓
DOCX generated
↓
DOCX validated
↓
PDF generated
↓
PDF validated
↓
DOCX/PDF consistency validated
↓
Visual validation completed
↓
Full resume preview shown
↓
DOCX download works
↓
PDF download works
↓
One-click regenerate works
```

 The final document must be a **complete tailored resume**, not a summary.

---

 # 68\. REAL DATA VALIDATION — MANDATORY

 Before generating any final document, verify that the data came from the uploaded resume.

 The system should internally store:

```
source_resume_id
source_resume_hash
source_resume_content
source_resume_model
```

 Generated content must reference the source resume.

 Do not allow a default fallback resume to silently enter the production workflow.

 If parsing fails:

```
STOP
```

 and show:

```
We couldn't reliably read your resume.
Please upload another file or try a DOCX version.
```

 Do not substitute demo data.

---

 # 69\. DEMO DATA ISOLATION

 If demo/sample data is needed for development:

 Store it separately, for example:

```
fixtures/
  sample_resume.docx
  sample_jd.txt
```

 Demo data must NEVER be used when processing a real user upload.

 Production flow must always use:

```
uploaded_file
```

 as the source.

---

 # 70\. RESUME IDENTITY VALIDATION

 Before final generation, verify that the final resume contains the original candidate identity.

 Check:

```
Original Name
Original Contact
Original Companies
Original Titles
```

 against the generated output.

 If the generated resume contains a different candidate name:

```
FAIL
```

 If the generated resume contains unrelated company names:

```
FAIL
```

 If default/sample data is detected:

```
FAIL
```

---

 # 71\. TEMPLATE COMPARISON

 Before and after document generation, compare:

```
Original Template
vs
Generated Template
```

 Generate a preservation score if useful.

 Example:

```
Template Preservation
94%
```

 Break down:

```
Layout: 96%
Typography: 98%
Sections: 100%
Images: 100%
Margins: 95%
Colors: 92%
```

 This score is optional for the user but useful internally.

 Do not claim exact preservation if the underlying document changed materially.

---

 # 72\. VISUAL DIFF — RECOMMENDED

 Where technically feasible, create rendered page images:

```
Original Page 1
Tailored Page 1

Original Page 2
Tailored Page 2
```

 Allow the developer/test suite to compare visual structure.

 The user-facing UI may optionally show:

```
Original
vs
Tailored
```

 for visual comparison.

---

 # 73\. PAGE COUNT AND TEMPLATE REQUIREMENT

 The system should prioritize:

```
Original Template
+
Original Page Structure
+
Readable Layout
+
Complete Resume
```

 If these requirements conflict:

 Priority should generally be:

```
1. Factual correctness
2. Complete resume
3. Original template preservation
4. Readability
5. Page count preservation
6. ATS optimization
```

 Never sacrifice factual correctness merely to fit a page.

 Never sacrifice readability merely to preserve page count.

---

 # 74\. ATS VS TEMPLATE BALANCE

 Do not destroy a good resume template merely to improve ATS keyword matching.

 The application should optimize within the user's existing structure.

 Prefer:

```
Improve wording
+
Improve keyword placement
+
Reorder relevant existing skills
+
Improve section emphasis
```

 rather than:

```
Throw away template
+
Create generic ATS resume
```

---

 # 75\. COMPLETE RESUME SECTION PRESERVATION

 If a section exists in the source resume, preserve it unless:

 - the user explicitly removes it
- it is invalid
- it is duplicated
- it is genuinely empty

 Potential sections:

```
Summary
Profile
Headline
Skills
Technical Skills
Core Competencies
Experience
Projects
Education
Certifications
Achievements
Awards
Publications
Languages
Volunteer Experience
Professional Affiliations
Interests
Additional Information
```

 The system should dynamically recognize sections rather than assuming a fixed resume format.

---

 # 76\. CONTENT LENGTH CONTROL

 Do not blindly make the resume longer.

 The AI should aim for:

```
Maximum relevance
+
Strong evidence
+
Concise language
+
Readable formatting
```

 Avoid unnecessary verbosity.

 Avoid repetitive keywords.

 Avoid duplicate bullets.

 Avoid meaningless filler.

---

 # 77\. BULLET REWRITING RULES

 When rewriting bullets:

 Prefer:

```
Action
+
Task
+
Technology/Method
+
Outcome
```

 when supported by the source resume.

 Do not invent metrics.

 If the original says:

```
Improved API performance.
```

 Do not generate:

```
Improved API performance by 45%.
```

 unless 45% exists in the source.

---

 # 78\. KEYWORD PLACEMENT STRATEGY

 When a keyword is supported by the resume, place it naturally in relevant locations.

 Potential locations:

 - summary
- headline
- skills
- experience bullets
- project descriptions

 Do not force keywords into irrelevant sections.

---

 # 79\. MISSING KEYWORDS

 Missing JD keywords should be shown separately.

 Example:

```
Missing / Not Evidenced

Kubernetes
Terraform
Azure DevOps
```

 Provide:

```
These keywords were not found in the uploaded resume
and were not added to avoid inventing experience.
```

---

 # 80\. USER EXPERIENCE FOR MISSING SKILLS

 Do not simply tell the user:

```
Missing Kubernetes
```

 Provide useful explanation:

```
Kubernetes
Status: Not evidenced

Why:
The uploaded resume does not provide reliable evidence
of Kubernetes experience.

Action:
Not added to the tailored resume.
```

---

 # 81\. FINAL RESULT INFORMATION

 The final page should display:

```
Tailored Resume Ready

ATS Compatibility
87 / 100

Original
74 / 100

Improvement
+13

Keyword Coverage
72% → 91%

Pages
3 → 3

Template Preservation
High

Validation
✓ Facts
✓ Completeness
✓ DOCX
✓ PDF
✓ Visual
```

---

 # 82\. DOWNLOADS

 Provide:

```
Download DOCX
Download PDF
Download Both
```

 These must point to actual generated files.

 Do not create fake URLs.

 Do not create fake downloads.

 Do not enable downloads until final validation succeeds.

---

 # 83\. DOWNLOAD FILE NAMING

 Use meaningful filenames.

 Example:

```
John_Doe_Tailored_Resume.docx
John_Doe_Tailored_Resume.pdf
```

 Sanitize filenames.

 Do not allow path traversal.

 If the name cannot be safely extracted:

```
Tailored_Resume.docx
Tailored_Resume.pdf
```

---

 # 84\. API DOWNLOAD SECURITY

 Downloads should use secure identifiers.

 Do not expose filesystem paths.

 Use:

```
file_id
```

 or secure signed download tokens.

 Validate that the requested file belongs to the relevant job/session.

---

 # 85\. README

 Create a useful README explaining:

 - project purpose
- architecture
- frontend setup
- backend setup
- Gemini API setup
- environment variables
- how to run
- how to test
- document generation requirements
- LibreOffice requirement
- OCR requirements if applicable
- DOCX template preservation
- PDF generation
- page-count handling
- ATS scoring
- explainable scoring
- suggested changes
- one-click regeneration
- validation pipeline
- troubleshooting
- current project status

 Keep `progress.md` as the source of truth for implementation progress.

---

 # 86\. ENVIRONMENT VARIABLES

 Create:

```
.env.example
```

 Include:

```
GEMINI_API_KEY=
GEMINI_MODEL=
```

 Add other required variables as needed.

 Never commit real API keys.

---

 # 87\. DEVELOPMENT WORKFLOW — MANDATORY

 For every development session:

```
1. Read progress.md
2. Inspect current project state
3. Identify current phase
4. Check Requested Changes
5. Inspect existing implementation
6. Implement the next required change
7. Run relevant tests
8. Fix failures
9. Verify the actual result
10. Update progress.md
11. Report what was completed
12. Report what remains
```

 Do NOT skip step 1.

 Do NOT skip step 10.

---

 # 88\. WHEN I ADD A CHANGE TO progress.md

 If I manually add:

```
## Requested Changes

- [ ] Add a preview page.
- [ ] Change the upload design.
- [ ] Improve DOCX formatting.
- [ ] Preserve original page count.
- [ ] Add one-click regeneration.
```

 Claude must treat these as active implementation tasks.

 After implementation:

```
## Requested Changes

- [x] Add a preview page.
- [x] Change the upload design.
- [ ] Improve DOCX formatting.
- [x] Preserve original page count.
- [x] Add one-click regeneration.
```

 Also update:

```
## Recently Completed Changes
```

 and:

```
## Files Modified
```

---

 # 89\. DO NOT ASK ME TO REPEAT PROJECT CONTEXT

 Use:

```
progress.md
```

 to maintain project continuity.

 If the project is reopened later, Claude should understand:

 - what has been built
- what has not been built
- what failed
- what needs fixing
- what the user requested
- what the next step should be

 without relying on the previous chat conversation.

---

 # 90\. WHEN SOMETHING FAILS

 Do not hide failures.

 Record them in:

```
## Known Issues
```

 Example:

```
- DOCX profile photo preservation fails for certain nested tables.
- LibreOffice is not installed in the current environment.
- Gemini returned incomplete JSON during one test.
- PDF text extraction failed for one scanned resume.
```

 Once fixed, document the solution.

---

 # 91\. FINAL END-TO-END QUALITY GATE

 Before declaring the application complete, the system must pass all of these:

 ### Input

```
✓ Real resume uploaded
✓ Real JD supplied
✓ No default resume data used
```

 ### Parsing

```
✓ Resume parsed
✓ JD parsed
✓ Page count detected
✓ Resume sections detected
```

 ### AI

```
✓ Gemini connected
✓ Complete resume generated
✓ Suggestions generated
✓ Source claims attached
```

 ### Accuracy

```
✓ No fabricated skills
✓ No fabricated companies
✓ No fabricated dates
✓ No fabricated metrics
✓ No fabricated certifications
✓ Original experience preserved
```

 ### User Control

```
✓ Suggestions displayed
✓ Individual changes can be accepted
✓ Individual changes can be rejected
✓ Apply All works
✓ Regenerate works
```

 ### ATS

```
✓ Original score calculated
✓ Tailored score calculated
✓ Score is deterministic
✓ Score is explainable
✓ Before/after coverage shown
```

 ### Documents

```
✓ DOCX generated
✓ PDF generated
✓ Original template preserved
✓ Profile photo preserved where possible
✓ Page count calculated
✓ Page layout validated
✓ DOCX content validated
✓ PDF content validated
✓ DOCX/PDF consistency validated
✓ Visual validation passed
```

 ### UI

```
✓ Full resume preview
✓ Page navigation
✓ ATS score
✓ Before/after coverage
✓ What changed
✓ Validation status
✓ Page count
✓ Download DOCX
✓ Download PDF
✓ Download Both
✓ Regenerate
```

---

 # 92\. FINAL COMPLETENESS RULE

 The final application must never consider this output sufficient:

```
Summary
Keywords
Recommendations
ATS Score
```

 That is analysis, not the final deliverable.

 The final deliverable must be:

```
COMPLETE TAILORED RESUME
+
ORIGINAL USER TEMPLATE
+
USER-APPROVED CHANGES
+
FACT VALIDATION
+
ATS ANALYSIS
+
DOCX
+
PDF
+
PAGE COUNT
+
VISUAL VALIDATION
+
CONTENT VALIDATION
+
FULL PREVIEW
+
DOWNLOADS
```

---

 # 93\. PRIORITY ORDER

 When implementation decisions conflict, use this priority:

```
1. Factual correctness
2. Use the actual uploaded resume
3. Complete resume preservation
4. No fabrication
5. User control over changes
6. Original template preservation
7. Document correctness
8. Visual quality
9. ATS optimization
10. UI polish
```

 A beautiful UI with fake document generation is not acceptable.

 A working backend that only generates a summary is not acceptable.

 A DOCX containing only a summary is not acceptable.

 A tailored resume using sample/default data is not acceptable.

 A resume that invents missing JD skills is not acceptable.

 A generated document that destroys the user's original template is not acceptable when preservation is technically possible.

 A document that passes text generation but has broken visual layout is not acceptable.

---

 # 94\. START NOW

 First:

 1. Inspect the existing project.
2. Create `progress.md` if it does not exist.
3. If it exists, read it.
4. Document the current project state.
5. Identify what has already been implemented.
6. Inspect existing frontend and backend architecture.
7. Identify where default/sample resume data is currently being used.
8. Replace the default-data workflow with actual uploaded-resume data.
9. Verify the current resume parsing pipeline.
10. Verify JD parsing.
11. Verify Gemini integration.
12. Verify complete resume generation.
13. Verify source-claim tracking.
14. Verify anti-fabrication validation.
15. Verify completeness validation.
16. Verify ATS scoring.
17. Verify explainable ATS scoring.
18. Verify before/after coverage.
19. Verify original-template preservation.
20. Implement page count.
21. Implement DOCX/PDF visual validation.
22. Implement DOCX/PDF content validation.
23. Implement user-controlled suggested changes.
24. Implement Apply Suggested Changes.
25. Implement one-click Regenerate.
26. Verify full preview.
27. Verify real DOCX/PDF downloads.
28. Run end-to-end tests.
29. Fix failures.
30. Update `progress.md`.

 Do not rebuild working features unnecessarily.

 Do not stop at a UI implementation.

 Do not stop at an AI analysis implementation.

 Do not stop at a summary.

 Continue until the actual uploaded resume can be transformed into a complete, factual, JD-tailored resume while retaining the user's original template as closely as technically possible.

---

 # 95\. NON-NEGOTIABLE FINAL REQUIREMENT

 The application exists to transform:

```
USER'S ACTUAL UPLOADED RESUME
                +
USER'S ACTUAL JOB DESCRIPTION
                ↓
        INTELLIGENT ANALYSIS
                ↓
     USER-CONTROLLED CHANGES
                ↓
       COMPLETE TAILORED RESUME
                ↓
   ORIGINAL TEMPLATE PRESERVED
                ↓
      FACT VALIDATION
                ↓
       ATS SCORING
                ↓
      PAGE COUNT CHECK
                ↓
        DOCX GENERATION
                ↓
         PDF GENERATION
                ↓
    CONTENT VALIDATION
                ↓
     VISUAL VALIDATION
                ↓
        FULL PREVIEW
                ↓
      REAL DOWNLOADS
```

 The final output must be a **complete tailored resume based on the user's actual uploaded resume**, not default data, not sample data, not a summary, and not a generic newly designed resume.

 The user's original template must be retained as closely as technically possible.

 The user must remain in control of suggested changes.

 The ATS score must be explainable.

 The before/after coverage must be visible.

 The final DOCX and PDF must be validated both visually and by content.

 The final page count must be calculated from the actual generated document.

 One-click regeneration must work without requiring the user to re-upload the resume and JD.

 At every stage:

 **`progress.md` is the single source of truth for project progress and requested changes.**

```

```