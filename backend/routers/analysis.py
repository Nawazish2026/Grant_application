from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Assessment, Mapping
from backend.schemas import (
    AnalysisResponse,
    CompletenessScore,
    MappingUpdate,
    MappingOut,
)
from backend.services.ai_analyzer import run_full_analysis, generate_summary
from backend.services.completeness import calculate_completeness

router = APIRouter(prefix="/api/assessments", tags=["analysis"])


@router.post("/{assessment_id}/analyze", response_model=AnalysisResponse)
async def trigger_analysis(assessment_id: str, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(404, "Assessment not found")

    if not assessment.guideline_text:
        raise HTTPException(400, "Upload a guideline document first.")
    if not assessment.application_text:
        raise HTTPException(400, "Upload an application document first.")

    result = await run_full_analysis(db, assessment_id)

    return AnalysisResponse(
        assessment_id=assessment_id,
        status=result["status"],
        message=result["message"],
    )


@router.patch("/{assessment_id}/mappings/{mapping_id}", response_model=MappingOut)
def update_mapping(
    assessment_id: str,
    mapping_id: str,
    payload: MappingUpdate,
    db: Session = Depends(get_db),
):
    mapping = db.query(Mapping).filter(Mapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(404, "Mapping not found")

    if mapping.requirement.assessment_id != assessment_id:
        raise HTTPException(404, "Mapping not found in this assessment")

    mapping.user_status = payload.user_status
    if payload.user_notes is not None:
        mapping.user_notes = payload.user_notes
    if payload.evidence_strength is not None:
        mapping.evidence_strength = payload.evidence_strength
    if payload.application_excerpt is not None:
        mapping.application_excerpt = payload.application_excerpt

    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if assessment:
        assessment.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(mapping)
    return mapping


@router.get("/{assessment_id}/completeness", response_model=CompletenessScore)
def get_completeness(assessment_id: str, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(404, "Assessment not found")

    score = calculate_completeness(db, assessment_id)
    if not score:
        raise HTTPException(404, "Assessment not found")

    return CompletenessScore(**score)


@router.get("/{assessment_id}/summary")
async def get_summary(assessment_id: str, regenerate: bool = False, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(404, "Assessment not found")

    if regenerate or not assessment.summary_report:
        summary = await generate_summary(db, assessment)
    else:
        summary = assessment.summary_report

    return {
        "assessment_id": assessment_id,
        "summary": summary,
        "is_stale": assessment.is_stale,
    }
