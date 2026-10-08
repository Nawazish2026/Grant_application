from sqlalchemy.orm import Session
from backend.models import Assessment, Requirement, Mapping


def calculate_completeness(db: Session, assessment_id: str) -> dict:
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        return {}

    requirements = (
        db.query(Requirement)
        .filter(Requirement.assessment_id == assessment_id)
        .all()
    )

    mandatory_total = 0
    mandatory_met = 0
    recommended_total = 0
    recommended_met = 0
    reviewed_count = 0
    pending_count = 0

    for req in requirements:
        is_met = False
        for mapping in req.mappings:
            if mapping.user_status in ("confirmed", "corrected", "rejected"):
                reviewed_count += 1
            else:
                pending_count += 1

            if mapping.user_status == "rejected":
                continue
            if mapping.user_status == "corrected":
                if mapping.evidence_strength == "met":
                    is_met = True
            elif mapping.evidence_strength == "met":
                is_met = True

        if req.is_mandatory:
            mandatory_total += 1
            if is_met:
                mandatory_met += 1
        else:
            recommended_total += 1
            if is_met:
                recommended_met += 1

    overall_total = mandatory_total + recommended_total
    overall_met = mandatory_met + recommended_met

    assessment.mandatory_total = mandatory_total
    assessment.mandatory_met = mandatory_met
    assessment.recommended_total = recommended_total
    assessment.recommended_met = recommended_met
    db.commit()

    return {
        "mandatory_total": mandatory_total,
        "mandatory_met": mandatory_met,
        "mandatory_pct": round(mandatory_met / mandatory_total * 100, 1) if mandatory_total else 0.0,
        "recommended_total": recommended_total,
        "recommended_met": recommended_met,
        "recommended_pct": round(recommended_met / recommended_total * 100, 1) if recommended_total else 0.0,
        "overall_total": overall_total,
        "overall_met": overall_met,
        "overall_pct": round(overall_met / overall_total * 100, 1) if overall_total else 0.0,
        "is_stale": assessment.is_stale,
        "reviewed_count": reviewed_count,
        "pending_count": pending_count,
    }
