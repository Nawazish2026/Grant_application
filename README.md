# Grant Application Completeness Assistant

An AI-powered tool that reviews draft funding applications against supplied grant guidelines, mapping requirements to evidence, identifying gaps, and producing a completeness assessment.

> ⚠️ **DISCLAIMER:** This tool provides advisory assessments only. It does not make authoritative legal or funding-eligibility decisions.

## Features

### AI Workflow
- **Requirement Extraction** — AI parses the grant guideline and extracts all eligibility and submission requirements
- **Evidence Mapping** — Maps each requirement to corresponding content in the draft application with source citations
- **Gap Detection** — Identifies missing, weak, or ambiguous evidence
- **Clarification Questions** — Generates targeted questions for weak areas
- **Unsupported Claims** — Flags application claims that lack supporting evidence
- **Mandatory vs Recommended** — Distinguishes required items from recommendations

### Application Features
- **Deterministic Completion Scoring** — Python-based logic calculates checklist completion (mandatory %, recommended %, overall %)
- **User Review** — Confirm, correct, or reject each AI mapping with notes
- **Supporting Document Tracking** — Track required supplementary documents (uploaded/missing)
- **Document Versioning** — SHA-256 hashing preserves document versions
- **Staleness Detection** — Marks assessment stale when either document changes
- **Summary Report** — Generates a comprehensive completeness summary

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ / FastAPI |
| AI | Google Gemini API (gemini-2.5-flash) |
| Database | SQLite (via SQLAlchemy) |
| Frontend | Vanilla HTML/CSS/JS |
| Document Parsing | PyPDF2, python-docx |

## Quick Start

### 1. Prerequisites
- Python 3.11+
- Google Gemini API key ([Get one here](https://aistudio.google.com/apikey))

### 2. Setup

```bash
# Clone and navigate to the project
cd Grant_application_completeness_assistant

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 3. Run

```bash
python run.py
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

### 4. Usage

1. **Create Assessment** — Click "New Assessment"
2. **Upload Guideline** — Upload the grant guideline (PDF, DOCX, or TXT)
3. **Upload Application** — Upload the draft application
4. **Run AI Analysis** — Click "Run AI Analysis" to extract requirements and map evidence
5. **Review Mappings** — Go to "Review Mappings" tab to confirm, correct, or reject each mapping
6. **Check Score** — View the deterministic completion score on the Upload tab
7. **View Summary** — See the full completeness report on the Summary tab

## Testing

```bash
# Install pytest
pip install pytest

# Run tests
pytest tests/ -v
```

### Sample Data
Sample documents are provided in `tests/sample_data/` for testing:
- `sample_guideline.txt` — Clean Energy Innovation Grant guidelines
- `sample_application.txt` — Draft application with intentional gaps

## Project Structure

```
├── run.py                          # Entry point
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment template
├── backend/
│   ├── main.py                     # FastAPI app
│   ├── config.py                   # Settings
│   ├── database.py                 # SQLite setup
│   ├── models.py                   # SQLAlchemy models
│   ├── schemas.py                  # Pydantic schemas
│   ├── routers/
│   │   ├── assessments.py          # CRUD + upload endpoints
│   │   └── analysis.py             # AI analysis + review endpoints
│   └── services/
│       ├── ai_analyzer.py          # Gemini integration
│       ├── completeness.py         # Deterministic scoring
│       ├── document_parser.py      # PDF/DOCX/TXT parsing
│       └── versioning.py           # Hash + staleness
├── frontend/
│   ├── index.html                  # Single page application
│   ├── css/styles.css              # Design system
│   └── js/
│       ├── api.js                  # API client
│       ├── components.js           # UI components
│       └── app.js                  # Application logic
└── tests/
    ├── test_completeness.py        # Scoring tests
    ├── test_versioning.py          # Versioning tests
    └── sample_data/                # Test documents
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/assessments` | Create assessment |
| GET | `/api/assessments` | List all assessments |
| GET | `/api/assessments/{id}` | Get assessment details |
| DELETE | `/api/assessments/{id}` | Delete assessment |
| POST | `/api/assessments/{id}/upload-guideline` | Upload guideline |
| POST | `/api/assessments/{id}/upload-application` | Upload application |
| POST | `/api/assessments/{id}/analyze` | Run AI analysis |
| PATCH | `/api/assessments/{id}/mappings/{mid}` | Update mapping (confirm/correct/reject) |
| GET | `/api/assessments/{id}/completeness` | Get completion score |
| GET | `/api/assessments/{id}/summary` | Get/regenerate summary |
| GET | `/api/assessments/{id}/staleness` | Check staleness |
| POST | `/api/assessments/{id}/supporting-docs` | Add supporting doc |
| PATCH | `/api/assessments/{id}/supporting-docs/{did}` | Update doc status |

## Architecture Decisions

1. **SQLite** — Chosen for zero-config simplicity. Sufficient for a single-user assessment tool.
2. **Deterministic Scoring** — Completion percentages are calculated with pure Python logic, not AI, ensuring reproducibility.
3. **SHA-256 Versioning** — Documents are hashed to detect changes and trigger staleness.
4. **Structured AI Output** — Gemini returns JSON-structured data that is stored in the database for deterministic post-processing.
5. **Advisory Disclaimer** — The tool explicitly states it does not make funding-eligibility decisions.
6. **Structured JSON Logging** — All AI workflow steps emit structured JSON logs with timing, assessment IDs, and result details.

## Limitations

- **Single-user tool** — No authentication or multi-user support. SQLite is not designed for concurrent writes.
- **Document size** — Input text is truncated to 50,000 characters per document to stay within Gemini token limits.
- **Supported formats** — PDF, DOCX, and TXT only. No OCR support for scanned PDFs.
- **AI accuracy** — Requirement extraction and mapping are AI-generated and may contain errors. The human review step is critical.
- **No real-time collaboration** — Designed for a single reviewer working through an assessment.
- **Gemini API dependency** — Requires a valid Gemini API key and internet access for AI analysis.

## Deployment

### Deploy to Railway (Recommended)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize and deploy
railway init
railway up

# Set environment variables
railway variables set GEMINI_API_KEY=your-key-here
```

### Deploy with Docker

```bash
docker build -t grant-assistant .
docker run -p 8000:8000 -e GEMINI_API_KEY=your-key-here grant-assistant
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | — | Google Gemini API key |
| `DATABASE_URL` | No | `sqlite:///./data/assessments.db` | Database connection string |
| `UPLOAD_DIR` | No | `./uploads` | Directory for uploaded files |
| `HOST` | No | `0.0.0.0` | Server bind address |
| `PORT` | No | `8000` | Server port |
