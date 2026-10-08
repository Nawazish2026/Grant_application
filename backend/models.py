import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from backend.database import Base


def generate_uuid():
    return str(uuid.uuid4())


def utcnow():
    return datetime.now(timezone.utc)


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False, default="Untitled Assessment")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    guideline_filename = Column(String(512), nullable=True)
    guideline_hash = Column(String(64), nullable=True)
    guideline_version = Column(Integer, default=1)
    guideline_uploaded_at = Column(DateTime, nullable=True)
    guideline_text = Column(Text, nullable=True)

    application_filename = Column(String(512), nullable=True)
    application_hash = Column(String(64), nullable=True)
    application_version = Column(Integer, default=1)
    application_uploaded_at = Column(DateTime, nullable=True)
    application_text = Column(Text, nullable=True)

    is_stale = Column(Boolean, default=False)
    stale_reason = Column(Text, nullable=True)

    analysis_status = Column(String(20), default="pending")
    analysis_error = Column(Text, nullable=True)

    mandatory_total = Column(Integer, default=0)
    mandatory_met = Column(Integer, default=0)
    recommended_total = Column(Integer, default=0)
    recommended_met = Column(Integer, default=0)

    summary_report = Column(Text, nullable=True)

    requirements = relationship(
        "Requirement", back_populates="assessment", cascade="all, delete-orphan"
    )
    supporting_docs = relationship(
        "SupportingDocument", back_populates="assessment", cascade="all, delete-orphan"
    )


class Requirement(Base):
    __tablename__ = "requirements"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    assessment_id = Column(String(36), ForeignKey("assessments.id"), nullable=False)
    requirement_text = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    is_mandatory = Column(Boolean, default=True)
    source_reference = Column(Text, nullable=True)
    order_index = Column(Integer, default=0)

    assessment = relationship("Assessment", back_populates="requirements")
    mappings = relationship(
        "Mapping", back_populates="requirement", cascade="all, delete-orphan"
    )
    clarification_questions = relationship(
        "ClarificationQuestion", back_populates="requirement", cascade="all, delete-orphan"
    )
    unsupported_claims = relationship(
        "UnsupportedClaim", back_populates="requirement", cascade="all, delete-orphan"
    )


class Mapping(Base):
    __tablename__ = "mappings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    requirement_id = Column(String(36), ForeignKey("requirements.id"), nullable=False)

    application_excerpt = Column(Text, nullable=True)
    application_reference = Column(Text, nullable=True)
    evidence_strength = Column(String(20), default="missing")
    ai_reasoning = Column(Text, nullable=True)

    user_status = Column(String(20), default="pending")
    user_notes = Column(Text, nullable=True)

    requirement = relationship("Requirement", back_populates="mappings")


class ClarificationQuestion(Base):
    __tablename__ = "clarification_questions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    requirement_id = Column(String(36), ForeignKey("requirements.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    priority = Column(String(20), default="medium")

    requirement = relationship("Requirement", back_populates="clarification_questions")


class UnsupportedClaim(Base):
    __tablename__ = "unsupported_claims"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    requirement_id = Column(String(36), ForeignKey("requirements.id"), nullable=True)
    claim_text = Column(Text, nullable=False)
    application_reference = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)

    requirement = relationship("Requirement", back_populates="unsupported_claims")


class SupportingDocument(Base):
    __tablename__ = "supporting_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    assessment_id = Column(String(36), ForeignKey("assessments.id"), nullable=False)
    document_name = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="missing")
    required_by = Column(Text, nullable=True)

    assessment = relationship("Assessment", back_populates="supporting_docs")
