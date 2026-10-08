import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import Base, engine, SessionLocal
from backend.models import Assessment, Requirement, Mapping
from backend.services.completeness import calculate_completeness


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _create_assessment_with_requirements(db, mandatory_count=3, recommended_count=2):
    assessment = Assessment(title="Test Assessment")
    db.add(assessment)
    db.flush()

    reqs = []
    for i in range(mandatory_count):
        req = Requirement(
            assessment_id=assessment.id,
            requirement_text=f"Mandatory Requirement {i+1}",
            is_mandatory=True,
            order_index=i,
        )
        db.add(req)
        reqs.append(req)

    for i in range(recommended_count):
        req = Requirement(
            assessment_id=assessment.id,
            requirement_text=f"Recommended Requirement {i+1}",
            is_mandatory=False,
            order_index=mandatory_count + i,
        )
        db.add(req)
        reqs.append(req)

    db.flush()
    return assessment, reqs


class TestCompletenessScoring:

    def test_empty_assessment(self, db):
        assessment = Assessment(title="Empty")
        db.add(assessment)
        db.commit()

        result = calculate_completeness(db, assessment.id)
        assert result["mandatory_total"] == 0
        assert result["mandatory_met"] == 0
        assert result["mandatory_pct"] == 0.0
        assert result["overall_pct"] == 0.0

    def test_all_met(self, db):
        assessment, reqs = _create_assessment_with_requirements(db, 3, 2)

        for req in reqs:
            mapping = Mapping(
                requirement_id=req.id,
                evidence_strength="met",
                user_status="confirmed",
            )
            db.add(mapping)

        db.commit()

        result = calculate_completeness(db, assessment.id)
        assert result["mandatory_total"] == 3
        assert result["mandatory_met"] == 3
        assert result["mandatory_pct"] == 100.0
        assert result["recommended_total"] == 2
        assert result["recommended_met"] == 2
        assert result["overall_pct"] == 100.0

    def test_partial_met(self, db):
        assessment, reqs = _create_assessment_with_requirements(db, 4, 0)

        for i, req in enumerate(reqs):
            mapping = Mapping(
                requirement_id=req.id,
                evidence_strength="met" if i < 2 else "missing",
                user_status="pending",
            )
            db.add(mapping)

        db.commit()

        result = calculate_completeness(db, assessment.id)
        assert result["mandatory_total"] == 4
        assert result["mandatory_met"] == 2
        assert result["mandatory_pct"] == 50.0

    def test_rejected_mappings_not_counted(self, db):
        assessment, reqs = _create_assessment_with_requirements(db, 2, 0)

        m1 = Mapping(
            requirement_id=reqs[0].id,
            evidence_strength="met",
            user_status="confirmed",
        )
        m2 = Mapping(
            requirement_id=reqs[1].id,
            evidence_strength="met",
            user_status="rejected",
        )
        db.add_all([m1, m2])
        db.commit()

        result = calculate_completeness(db, assessment.id)
        assert result["mandatory_met"] == 1
        assert result["mandatory_pct"] == 50.0

    def test_corrected_mapping_with_met_strength(self, db):
        assessment, reqs = _create_assessment_with_requirements(db, 1, 0)

        mapping = Mapping(
            requirement_id=reqs[0].id,
            evidence_strength="met",
            user_status="corrected",
        )
        db.add(mapping)
        db.commit()

        result = calculate_completeness(db, assessment.id)
        assert result["mandatory_met"] == 1

    def test_corrected_mapping_with_partial_strength(self, db):
        assessment, reqs = _create_assessment_with_requirements(db, 1, 0)

        mapping = Mapping(
            requirement_id=reqs[0].id,
            evidence_strength="partial",
            user_status="corrected",
        )
        db.add(mapping)
        db.commit()

        result = calculate_completeness(db, assessment.id)
        assert result["mandatory_met"] == 0

    def test_review_counts(self, db):
        assessment, reqs = _create_assessment_with_requirements(db, 3, 0)

        m1 = Mapping(requirement_id=reqs[0].id, evidence_strength="met", user_status="confirmed")
        m2 = Mapping(requirement_id=reqs[1].id, evidence_strength="met", user_status="pending")
        m3 = Mapping(requirement_id=reqs[2].id, evidence_strength="missing", user_status="rejected")
        db.add_all([m1, m2, m3])
        db.commit()

        result = calculate_completeness(db, assessment.id)
        assert result["reviewed_count"] == 2
        assert result["pending_count"] == 1

    def test_separate_mandatory_recommended_scores(self, db):
        assessment, reqs = _create_assessment_with_requirements(db, 2, 2)

        for req in reqs:
            strength = "met" if req.is_mandatory else "missing"
            mapping = Mapping(
                requirement_id=req.id,
                evidence_strength=strength,
                user_status="pending",
            )
            db.add(mapping)
        db.commit()

        result = calculate_completeness(db, assessment.id)
        assert result["mandatory_pct"] == 100.0
        assert result["recommended_pct"] == 0.0
        assert result["overall_pct"] == 50.0

    def test_nonexistent_assessment(self, db):
        result = calculate_completeness(db, "nonexistent-id")
        assert result == {}
