import os
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Assessment, SupportingDocument
from backend.schemas import (
    AssessmentCreate,
    AssessmentDetail,
    AssessmentSummary,
    SupportingDocCreate,
    SupportingDocOut,
    SupportingDocUpdate,
)
from backend.services.document_parser import parse_document
from backend.services.versioning import check_staleness, update_document_version
from backend.config import settings

router = APIRouter(prefix="/api/assessments", tags=["assessments"])


@router.post("", response_model=AssessmentSummary, status_code=201)
def create_assessment(payload: AssessmentCreate, db: Session = Depends(get_db)):
    assessment = Assessment(title=payload.title)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.get("", response_model=List[AssessmentSummary])
def list_assessments(db: Session = Depends(get_db)):
    return db.query(Assessment).order_by(Assessment.updated_at.desc()).all()


@router.get("/{assessment_id}", response_model=AssessmentDetail)
def get_assessment(assessment_id: str, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(404, "Assessment not found")
    return assessment


@router.delete("/{assessment_id}", status_code=204)
def delete_assessment(assessment_id: str, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(404, "Assessment not found")
    db.delete(assessment)
    db.commit()


@router.post("/{assessment_id}/upload-guideline")
async def upload_guideline(
    assessment_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(404, "Assessment not found")

    file_bytes = await file.read()
    try:
        text, file_hash = parse_document(file.filename, file_bytes)
    except ValueError as e:
        raise HTTPException(400, str(e))

    is_stale, stale_reason = check_staleness(assessment, file_hash, "guideline")
    if is_stale:
        assessment.is_stale = True
        assessment.stale_reason = stale_reason

    update_document_version(assessment, "guideline", file.filename, file_hash, text)

    upload_dir = os.path.join(settings.upload_dir, assessment_id)
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, f"guideline_{file.filename}")
    with open(filepath, "wb") as f:
        f.write(file_bytes)

    db.commit()
    db.refresh(assessment)

    return {
        "message": "Guideline uploaded successfully",
        "filename": file.filename,
        "version": assessment.guideline_version,
        "is_stale": assessment.is_stale,
        "stale_reason": assessment.stale_reason,
        "text_length": len(text),
    }


@router.post("/{assessment_id}/upload-application")
async def upload_application(
    assessment_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(404, "Assessment not found")

    file_bytes = await file.read()
    try:
        text, file_hash = parse_document(file.filename, file_bytes)
    except ValueError as e:
        raise HTTPException(400, str(e))

    is_stale, stale_reason = check_staleness(assessment, file_hash, "application")
    if is_stale:
        assessment.is_stale = True
        assessment.stale_reason = stale_reason

    update_document_version(assessment, "application", file.filename, file_hash, text)

    upload_dir = os.path.join(settings.upload_dir, assessment_id)
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, f"application_{file.filename}")
    with open(filepath, "wb") as f:
        f.write(file_bytes)

    db.commit()
    db.refresh(assessment)

    return {
        "message": "Application uploaded successfully",
        "filename": file.filename,
        "version": assessment.application_version,
        "is_stale": assessment.is_stale,
        "stale_reason": assessment.stale_reason,
        "text_length": len(text),
    }


@router.post("/{assessment_id}/supporting-docs", response_model=SupportingDocOut, status_code=201)
def add_supporting_doc(
    assessment_id: str,
    payload: SupportingDocCreate,
    db: Session = Depends(get_db),
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(404, "Assessment not found")

    doc = SupportingDocument(
        assessment_id=assessment_id,
        document_name=payload.document_name,
        description=payload.description,
        status=payload.status,
        required_by=payload.required_by,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.patch("/{assessment_id}/supporting-docs/{doc_id}", response_model=SupportingDocOut)
def update_supporting_doc(
    assessment_id: str,
    doc_id: str,
    payload: SupportingDocUpdate,
    db: Session = Depends(get_db),
):
    doc = (
        db.query(SupportingDocument)
        .filter(SupportingDocument.id == doc_id, SupportingDocument.assessment_id == assessment_id)
        .first()
    )
    if not doc:
        raise HTTPException(404, "Supporting document not found")

    if payload.status is not None:
        doc.status = payload.status
    if payload.description is not None:
        doc.description = payload.description

    db.commit()
    db.refresh(doc)
    return doc


@router.get("/{assessment_id}/staleness")
def check_assessment_staleness(assessment_id: str, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(404, "Assessment not found")
    return {
        "is_stale": assessment.is_stale,
        "stale_reason": assessment.stale_reason,
        "guideline_version": assessment.guideline_version,
        "application_version": assessment.application_version,
    }
