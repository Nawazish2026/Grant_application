from __future__ import annotations

import json
import logging
import time

from google import genai
from google.genai import types
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import (
    Assessment,
    Requirement,
    Mapping,
    ClarificationQuestion,
    UnsupportedClaim,
    SupportingDocument,
)

logger = logging.getLogger(__name__)


def _get_client():
    return genai.Client(api_key=settings.gemini_api_key)


FALLBACK_MODELS = [
    settings.gemini_model,
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
    "gemini-3.8-flash",
]


def _call_gemini(
    prompt: str,
    temperature: float = 0.1,
    max_output_tokens: int = 8192,
    is_json: bool = False,
) -> str:
    """Robust Gemini caller with exponential retry and model fallback pool for high resilience."""
    client = _get_client()
    models_to_try = []
    for m in FALLBACK_MODELS:
        if m and m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for model_name in models_to_try:
        for attempt in range(2):
            try:
                logger.info(f"Calling Gemini model: {model_name} (attempt {attempt + 1}, is_json={is_json})")
                config_kwargs = {
                    "temperature": temperature,
                    "max_output_tokens": max_output_tokens,
                }
                if is_json:
                    config_kwargs["response_mime_type"] = "application/json"

                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(**config_kwargs),
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                last_error = e
                err_str = str(e)
                logger.warning(f"Model {model_name} attempt {attempt + 1} failed: {err_str[:120]}")
                if "503" in err_str or "429" in err_str:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                else:
                    break

    raise RuntimeError(f"All Gemini models in fallback pool failed. Last error: {last_error}")




EXTRACT_REQUIREMENTS_PROMPT = """You are an expert grant compliance analyst. Analyze the following grant/funding guideline document and extract ALL eligibility and submission requirements.

For each requirement, provide:
1. requirement_text: Clear description of the requirement
2. category: Category (e.g., "Eligibility", "Budget", "Narrative", "Attachments", "Timeline", "Organizational", "Technical", "Compliance")
3. is_mandatory: true if this is a MANDATORY requirement, false if it is a RECOMMENDATION or nice-to-have
4. source_reference: The exact section, page number, or paragraph where this requirement appears in the guideline

Also identify any supporting documents that the guideline requires applicants to submit.

GUIDELINE DOCUMENT:
---
{guideline_text}
---

Return your response as valid JSON with this exact structure:
{{
  "requirements": [
    {{
      "requirement_text": "...",
      "category": "...",
      "is_mandatory": true/false,
      "source_reference": "..."
    }}
  ],
  "required_supporting_documents": [
    {{
      "document_name": "...",
      "description": "...",
      "required_by": "..."
    }}
  ]
}}

Be thorough. Extract EVERY requirement mentioned. Distinguish clearly between mandatory requirements and recommendations/suggestions."""


MAP_APPLICATION_PROMPT = """You are an expert grant compliance analyst. You have a list of requirements extracted from a grant guideline, and a draft application. Your job is to map each requirement to the relevant content in the application.

For each requirement, find the corresponding evidence in the application and assess it.

REQUIREMENTS:
---
{requirements_json}
---

APPLICATION DOCUMENT:
---
{application_text}
---

For each requirement (identified by its index), provide:
1. application_excerpt: Direct quote from the application (keep under 25 words)
2. application_reference: Section/heading where this excerpt appears
3. evidence_strength: One of "met", "partial", "missing", "ambiguous"
4. ai_reasoning: Concise explanation (1-2 sentences)
5. clarification_questions: Array of {{"question_text": "...", "priority": "high|medium|low"}} for weak/missing evidence (or empty [])
6. unsupported_claims: Array of {{"claim_text": "...", "application_reference": "...", "explanation": "..."}} (or empty [])

Return valid JSON with key "mappings" containing an array of mapping objects:
{{
  "mappings": [
    {{
      "requirement_index": 0,
      "application_excerpt": "...",
      "application_reference": "...",
      "evidence_strength": "met",
      "ai_reasoning": "...",
      "clarification_questions": [],
      "unsupported_claims": []
    }}
  ]
}}
Keep responses concise to ensure full coverage without truncation."""


GENERATE_SUMMARY_PROMPT = """You are an expert grant compliance analyst. Generate a comprehensive completeness summary report for this grant application assessment.

IMPORTANT: This is an ADVISORY assessment only. Do NOT make authoritative legal or funding-eligibility decisions.

ASSESSMENT DATA:
---
{assessment_json}
---

Generate a well-structured markdown report that includes:
1. Executive Summary with overall readiness assessment (advisory only)
2. Completion Statistics with mandatory and recommended requirements breakdown
3. Strengths where the application is strong
4. Gaps and Weaknesses for mandatory items missing or partially met
5. Key Clarification Questions as a prioritized list
6. Unsupported Claims that need evidence
7. Missing Supporting Documents if any
8. Recommendations as prioritized action items to strengthen the application

Include this disclaimer prominently:
"DISCLAIMER: This assessment is advisory only and does not constitute an authoritative legal or funding-eligibility decision. Applicants should verify all requirements with the funding agency."

Write clearly and professionally."""


def _clean_json_response(text):
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _parse_json_safe(raw_text: str) -> dict:
    clean_text = _clean_json_response(raw_text)
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        start_obj = clean_text.find("{")
        end_obj = clean_text.rfind("}")
        if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
            try:
                return json.loads(clean_text[start_obj:end_obj + 1])
            except json.JSONDecodeError:
                pass
        for suffix in ["}]}", "]}", '"}]}', '"]}', "}", "]"]:
            try:
                return json.loads(clean_text.rstrip() + suffix)
            except json.JSONDecodeError:
                pass
        raise


async def extract_requirements(db: Session, assessment: Assessment) -> list[dict]:
    if not assessment.guideline_text:
        raise ValueError("No guideline document uploaded.")

    start = time.time()
    logger.info(
        "Starting requirement extraction",
        extra={"assessment_id": assessment.id, "workflow_step": "extract_requirements", "details": {"guideline_length": len(assessment.guideline_text)}},
    )

    prompt = EXTRACT_REQUIREMENTS_PROMPT.format(
        guideline_text=assessment.guideline_text[:50000]
    )
    raw_text = _call_gemini(prompt, temperature=0.1, max_output_tokens=8192, is_json=True)

    try:
        data = _parse_json_safe(raw_text)
    except json.JSONDecodeError as e:
        logger.error(
            f"Failed to parse requirements JSON: {e}",
            extra={"assessment_id": assessment.id, "workflow_step": "extract_requirements", "details": {"raw_response_preview": raw_text[:300]}},
        )
        raise ValueError(f"AI returned invalid JSON: {e}")

    for req in assessment.requirements:
        db.delete(req)
    for doc in assessment.supporting_docs:
        db.delete(doc)
    db.flush()

    requirements = data.get("requirements", [])
    for i, req_data in enumerate(requirements):
        req = Requirement(
            assessment_id=assessment.id,
            requirement_text=req_data.get("requirement_text", ""),
            category=req_data.get("category", "General"),
            is_mandatory=req_data.get("is_mandatory", True),
            source_reference=req_data.get("source_reference", ""),
            order_index=i,
        )
        db.add(req)

    supporting_docs = data.get("required_supporting_documents", [])
    for doc_data in supporting_docs:
        doc = SupportingDocument(
            assessment_id=assessment.id,
            document_name=doc_data.get("document_name", ""),
            description=doc_data.get("description", ""),
            status="missing",
            required_by=doc_data.get("required_by", ""),
        )
        db.add(doc)

    db.commit()

    elapsed = round((time.time() - start) * 1000)
    logger.info(
        "Requirement extraction completed",
        extra={"assessment_id": assessment.id, "workflow_step": "extract_requirements", "duration_ms": elapsed, "details": {"requirements_found": len(requirements), "supporting_docs_found": len(supporting_docs)}},
    )

    return requirements


async def map_application(db: Session, assessment: Assessment) -> list[dict]:
    if not assessment.application_text:
        raise ValueError("No application document uploaded.")

    start = time.time()
    logger.info(
        "Starting application mapping",
        extra={"assessment_id": assessment.id, "workflow_step": "map_application", "details": {"application_length": len(assessment.application_text)}},
    )

    requirements = (
        db.query(Requirement)
        .filter(Requirement.assessment_id == assessment.id)
        .order_by(Requirement.order_index)
        .all()
    )

    if not requirements:
        raise ValueError("No requirements extracted. Run extraction first.")

    for req in requirements:
        for m in req.mappings:
            db.delete(m)
        for q in req.clarification_questions:
            db.delete(q)
        for c in req.unsupported_claims:
            db.delete(c)
    db.flush()

    CHUNK_SIZE = 8
    mappings_data = []

    for chunk_start in range(0, len(requirements), CHUNK_SIZE):
        chunk_reqs = requirements[chunk_start:chunk_start + CHUNK_SIZE]
        req_json = [
            {
                "index": chunk_start + i,
                "requirement_text": r.requirement_text,
                "category": r.category,
                "is_mandatory": r.is_mandatory,
            }
            for i, r in enumerate(chunk_reqs)
        ]

        prompt = MAP_APPLICATION_PROMPT.format(
            requirements_json=json.dumps(req_json, indent=2),
            application_text=assessment.application_text[:50000],
        )
        raw_text = _call_gemini(prompt, temperature=0.1, max_output_tokens=8192, is_json=True)

        try:
            data = _parse_json_safe(raw_text)
            chunk_items = data if isinstance(data, list) else data.get("mappings", [])
            mappings_data.extend(chunk_items)
        except json.JSONDecodeError as e:
            logger.warning(
                f"Failed to parse mapping JSON chunk starting at {chunk_start}: {e}",
                extra={"assessment_id": assessment.id, "workflow_step": "map_application", "details": {"raw_response_preview": raw_text[:300]}},
            )

    strength_counts = {"met": 0, "partial": 0, "missing": 0, "ambiguous": 0}
    questions_count = 0
    claims_count = 0

    for mapping_data in mappings_data:
        req_idx = mapping_data.get("requirement_index", 0)
        if req_idx < len(requirements):
            req = requirements[req_idx]

            strength = mapping_data.get("evidence_strength", "missing")
            strength_counts[strength] = strength_counts.get(strength, 0) + 1

            mapping = Mapping(
                requirement_id=req.id,
                application_excerpt=mapping_data.get("application_excerpt", ""),
                application_reference=mapping_data.get("application_reference", ""),
                evidence_strength=strength,
                ai_reasoning=mapping_data.get("ai_reasoning", ""),
                user_status="pending",
            )
            db.add(mapping)

            for q_data in mapping_data.get("clarification_questions", []):
                question = ClarificationQuestion(
                    requirement_id=req.id,
                    question_text=q_data.get("question_text", ""),
                    priority=q_data.get("priority", "medium"),
                )
                db.add(question)
                questions_count += 1

            for c_data in mapping_data.get("unsupported_claims", []):
                claim = UnsupportedClaim(
                    requirement_id=req.id,
                    claim_text=c_data.get("claim_text", ""),
                    application_reference=c_data.get("application_reference", ""),
                    explanation=c_data.get("explanation", ""),
                )
                db.add(claim)
                claims_count += 1

    db.commit()

    elapsed = round((time.time() - start) * 1000)
    logger.info(
        "Application mapping completed",
        extra={"assessment_id": assessment.id, "workflow_step": "map_application", "duration_ms": elapsed, "details": {"mappings_created": len(mappings_data), "evidence_strength": strength_counts, "clarification_questions": questions_count, "unsupported_claims": claims_count}},
    )

    return mappings_data


async def generate_summary(db: Session, assessment: Assessment) -> str:
    requirements = (
        db.query(Requirement)
        .filter(Requirement.assessment_id == assessment.id)
        .order_by(Requirement.order_index)
        .all()
    )

    assessment_data = {
        "title": assessment.title,
        "guideline": assessment.guideline_filename,
        "guideline_version": assessment.guideline_version,
        "application": assessment.application_filename,
        "application_version": assessment.application_version,
        "is_stale": assessment.is_stale,
        "stale_reason": assessment.stale_reason,
        "requirements": [],
        "supporting_documents": [],
    }

    for req in requirements:
        req_data = {
            "requirement": req.requirement_text,
            "category": req.category,
            "is_mandatory": req.is_mandatory,
            "source_reference": req.source_reference,
            "mappings": [],
            "clarification_questions": [],
            "unsupported_claims": [],
        }
        for m in req.mappings:
            req_data["mappings"].append({
                "evidence_strength": m.evidence_strength,
                "application_excerpt": m.application_excerpt,
                "ai_reasoning": m.ai_reasoning,
                "user_status": m.user_status,
                "user_notes": m.user_notes,
            })
        for q in req.clarification_questions:
            req_data["clarification_questions"].append({
                "question": q.question_text,
                "priority": q.priority,
            })
        for c in req.unsupported_claims:
            req_data["unsupported_claims"].append({
                "claim": c.claim_text,
                "explanation": c.explanation,
            })
        assessment_data["requirements"].append(req_data)

    for doc in assessment.supporting_docs:
        assessment_data["supporting_documents"].append({
            "name": doc.document_name,
            "status": doc.status,
            "description": doc.description,
        })

    prompt = GENERATE_SUMMARY_PROMPT.format(
        assessment_json=json.dumps(assessment_data, indent=2)[:30000]
    )
    summary = _call_gemini(prompt, temperature=0.2, max_output_tokens=4096)
    assessment.summary_report = summary
    db.commit()

    return summary


async def run_full_analysis(db: Session, assessment_id: str) -> dict:
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise ValueError("Assessment not found.")

    total_start = time.time()
    logger.info(
        "Starting full analysis pipeline",
        extra={"assessment_id": assessment_id, "workflow_step": "full_analysis", "details": {"guideline": assessment.guideline_filename, "application": assessment.application_filename}},
    )

    assessment.analysis_status = "running"
    assessment.analysis_error = None
    assessment.is_stale = False
    assessment.stale_reason = None
    db.commit()

    try:
        await extract_requirements(db, assessment)
        await map_application(db, assessment)
        await generate_summary(db, assessment)

        assessment.analysis_status = "completed"
        db.commit()

        elapsed = round((time.time() - total_start) * 1000)
        logger.info(
            "Full analysis pipeline completed",
            extra={"assessment_id": assessment_id, "workflow_step": "full_analysis", "duration_ms": elapsed},
        )

        return {"status": "completed", "message": "Analysis completed successfully."}

    except Exception as e:
        elapsed = round((time.time() - total_start) * 1000)
        logger.error(
            f"Analysis pipeline failed: {e}",
            extra={"assessment_id": assessment_id, "workflow_step": "full_analysis", "duration_ms": elapsed, "details": {"error": str(e)}},
        )
        assessment.analysis_status = "failed"
        assessment.analysis_error = str(e)
        db.commit()
        return {"status": "failed", "message": str(e)}
