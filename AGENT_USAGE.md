# AGENT_USAGE.md

## Tools Used

- **Google Gemini 2.5 Flash** — Primary AI model for all analysis tasks (requirement extraction, evidence mapping, summary generation)
- **Antigravity IDE (Claude)** — AI coding assistant used for code generation, architecture decisions, and iterative development
- **Python 3.11+ / FastAPI** — Backend framework
- **SQLAlchemy** — ORM for database models and queries
- **PyPDF2 / python-docx** — Document parsing libraries

## Representative Prompts

### Architecture Planning
> "Build an application that reviews a draft funding application against a supplied grant guideline. Inputs: grant guideline document, draft application, optional supporting-document metadata."

### AI Workflow Design
> "Extract eligibility and submission requirements from the guideline. Map application content to each requirement. Cite the source supporting every mapping."

### Frontend Development
> "Create a single-page application with tabs for Upload, Requirements, Review Mappings, Supporting Documents, and Summary."

### Testing
> "Write focused tests for the deterministic completeness scoring logic and the document versioning/staleness detection."

## Delegated Work

| Task | Delegated To | Outcome |
|------|-------------|---------|
| Requirement extraction from guidelines | Gemini 2.5 Flash | AI parses guideline text and returns structured JSON with requirements, categories, mandatory flags, and source references |
| Evidence mapping | Gemini 2.5 Flash | AI maps each requirement to application content with excerpts, citations, and strength assessments |
| Gap identification | Gemini 2.5 Flash | AI identifies missing/weak/ambiguous evidence and generates clarification questions |
| Unsupported claim detection | Gemini 2.5 Flash | AI flags claims in the application that lack supporting evidence |
| Summary report generation | Gemini 2.5 Flash | AI generates a structured markdown completeness report |
| Completeness scoring | Deterministic Python logic | NOT delegated to AI — pure Python calculation based on mapping statuses |

## Important Agent Mistakes and Rejected Suggestions

1. **Over-commenting**: The AI assistant initially generated code with excessive inline comments and ASCII art section dividers. These were stripped in a cleanup pass to keep the codebase clean and professional.

2. **Redundant imports**: Several generated files included unused imports (e.g., `Any` from typing, `Form` from FastAPI). These were caught and removed during code review.

3. **DateTime handling**: The agent initially placed `datetime` imports inside function bodies rather than at the module level. This was corrected for consistency.

4. **Config class pattern**: Used `class Config` in Pydantic models which triggers a deprecation warning in Pydantic V2. This is a known issue but was kept for compatibility with the installed version.

## How I Verified the Output

### Automated Testing
- **19 unit tests** covering:
  - Completeness scoring logic (9 tests): empty assessments, all met, partial met, rejected mappings, corrected mappings, review counts, separate mandatory/recommended scores
  - Versioning and staleness detection (10 tests): first upload, hash changes, version increments, SHA-256 verification

### Manual Testing
- Created assessments, uploaded sample guideline and application documents
- Ran AI analysis end-to-end and verified requirement extraction accuracy
- Reviewed AI mappings — confirmed, corrected, and rejected individual mappings
- Verified completeness score updates after each review action
- Tested staleness detection by re-uploading modified documents
- Verified summary report generation includes disclaimer
- Tested all UI states: empty, loading, success, error, validation
- Tested drag-and-drop file upload and click-to-browse
- Verified supporting document tracking (add, update status)

### Code Review
- Reviewed all AI-generated code for correctness
- Verified API response schemas match frontend expectations
- Confirmed no API keys or secrets in committed code
- Validated that deterministic scoring uses pure Python logic (no AI)
