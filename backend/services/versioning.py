from datetime import datetime, timezone
from typing import Optional, Tuple
from backend.models import Assessment


def check_staleness(
    assessment: Assessment,
    new_hash: Optional[str] = None,
    document_type: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    if document_type == "guideline" and new_hash:
        if assessment.guideline_hash and new_hash != assessment.guideline_hash:
            return True, (
                f"Guideline document changed (version {assessment.guideline_version} → "
                f"{assessment.guideline_version + 1}). "
                "Previous analysis may no longer be accurate."
            )
    elif document_type == "application" and new_hash:
        if assessment.application_hash and new_hash != assessment.application_hash:
            return True, (
                f"Application document changed (version {assessment.application_version} → "
                f"{assessment.application_version + 1}). "
                "Previous analysis may no longer be accurate."
            )
    return False, None


def update_document_version(
    assessment: Assessment,
    document_type: str,
    filename: str,
    file_hash: str,
    extracted_text: str,
) -> None:
    now = datetime.now(timezone.utc)

    if document_type == "guideline":
        if assessment.guideline_hash and file_hash != assessment.guideline_hash:
            assessment.guideline_version += 1
        assessment.guideline_filename = filename
        assessment.guideline_hash = file_hash
        assessment.guideline_uploaded_at = now
        assessment.guideline_text = extracted_text
    elif document_type == "application":
        if assessment.application_hash and file_hash != assessment.application_hash:
            assessment.application_version += 1
        assessment.application_filename = filename
        assessment.application_hash = file_hash
        assessment.application_uploaded_at = now
        assessment.application_text = extracted_text

    assessment.updated_at = now
