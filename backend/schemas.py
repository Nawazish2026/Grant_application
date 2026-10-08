from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class SupportingDocCreate(BaseModel):
    document_name: str
    description: Optional[str] = None
    status: str = "missing"
    required_by: Optional[str] = None


class SupportingDocOut(SupportingDocCreate):
    id: str

    class Config:
        from_attributes = True


class SupportingDocUpdate(BaseModel):
    status: Optional[str] = None
    description: Optional[str] = None


class MappingOut(BaseModel):
    id: str
    application_excerpt: Optional[str] = None
    application_reference: Optional[str] = None
    evidence_strength: str = "missing"
    ai_reasoning: Optional[str] = None
    user_status: str = "pending"
    user_notes: Optional[str] = None

    class Config:
        from_attributes = True


class MappingUpdate(BaseModel):
    user_status: str = Field(..., pattern="^(confirmed|corrected|rejected)$")
    user_notes: Optional[str] = None
    evidence_strength: Optional[str] = None
    application_excerpt: Optional[str] = None


class ClarificationQuestionOut(BaseModel):
    id: str
    question_text: str
    priority: str = "medium"

    class Config:
        from_attributes = True


class UnsupportedClaimOut(BaseModel):
    id: str
    claim_text: str
    application_reference: Optional[str] = None
    explanation: Optional[str] = None

    class Config:
        from_attributes = True


class RequirementOut(BaseModel):
    id: str
    requirement_text: str
    category: Optional[str] = None
    is_mandatory: bool = True
    source_reference: Optional[str] = None
    order_index: int = 0
    mappings: List[MappingOut] = []
    clarification_questions: List[ClarificationQuestionOut] = []
    unsupported_claims: List[UnsupportedClaimOut] = []

    class Config:
        from_attributes = True


class AssessmentCreate(BaseModel):
    title: str = "Untitled Assessment"


class AssessmentSummary(BaseModel):
    id: str
    title: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    guideline_filename: Optional[str] = None
    application_filename: Optional[str] = None
    analysis_status: str = "pending"
    is_stale: bool = False
    mandatory_total: int = 0
    mandatory_met: int = 0
    recommended_total: int = 0
    recommended_met: int = 0

    class Config:
        from_attributes = True


class AssessmentDetail(AssessmentSummary):
    guideline_hash: Optional[str] = None
    guideline_version: int = 1
    guideline_uploaded_at: Optional[datetime] = None
    application_hash: Optional[str] = None
    application_version: int = 1
    application_uploaded_at: Optional[datetime] = None
    stale_reason: Optional[str] = None
    analysis_error: Optional[str] = None
    summary_report: Optional[str] = None
    requirements: List[RequirementOut] = []
    supporting_docs: List[SupportingDocOut] = []

    class Config:
        from_attributes = True


class CompletenessScore(BaseModel):
    mandatory_total: int
    mandatory_met: int
    mandatory_pct: float
    recommended_total: int
    recommended_met: int
    recommended_pct: float
    overall_total: int
    overall_met: int
    overall_pct: float
    is_stale: bool
    reviewed_count: int
    pending_count: int


class AnalysisResponse(BaseModel):
    assessment_id: str
    status: str
    message: str
