import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import Base, engine, SessionLocal
from backend.models import Assessment
from backend.services.versioning import check_staleness, update_document_version
from backend.services.document_parser import compute_file_hash


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


class TestStalenessDetection:

    def test_no_staleness_on_first_upload(self, db):
        assessment = Assessment(title="Test")
        db.add(assessment)
        db.commit()

        is_stale, reason = check_staleness(assessment, "abc123", "guideline")
        assert is_stale is False
        assert reason is None

    def test_staleness_on_guideline_change(self, db):
        assessment = Assessment(title="Test", guideline_hash="hash_v1")
        db.add(assessment)
        db.commit()

        is_stale, reason = check_staleness(assessment, "hash_v2", "guideline")
        assert is_stale is True
        assert "Guideline document changed" in reason

    def test_no_staleness_on_same_guideline(self, db):
        assessment = Assessment(title="Test", guideline_hash="same_hash")
        db.add(assessment)
        db.commit()

        is_stale, reason = check_staleness(assessment, "same_hash", "guideline")
        assert is_stale is False

    def test_staleness_on_application_change(self, db):
        assessment = Assessment(title="Test", application_hash="hash_v1")
        db.add(assessment)
        db.commit()

        is_stale, reason = check_staleness(assessment, "hash_v2", "application")
        assert is_stale is True
        assert "Application document changed" in reason


class TestVersionTracking:

    def test_first_upload_sets_version_1(self, db):
        assessment = Assessment(title="Test")
        db.add(assessment)
        db.commit()

        update_document_version(assessment, "guideline", "guide.pdf", "hash1", "text")
        assert assessment.guideline_version == 1
        assert assessment.guideline_filename == "guide.pdf"
        assert assessment.guideline_hash == "hash1"

    def test_version_increments_on_change(self, db):
        assessment = Assessment(title="Test", guideline_hash="hash_v1", guideline_version=1)
        db.add(assessment)
        db.commit()

        update_document_version(assessment, "guideline", "guide_v2.pdf", "hash_v2", "new text")
        assert assessment.guideline_version == 2

    def test_version_stays_on_same_file(self, db):
        assessment = Assessment(title="Test", guideline_hash="same_hash", guideline_version=1)
        db.add(assessment)
        db.commit()

        update_document_version(assessment, "guideline", "guide.pdf", "same_hash", "same text")
        assert assessment.guideline_version == 1


class TestFileHashing:

    def test_same_content_same_hash(self):
        content = b"Hello, World!"
        h1 = compute_file_hash(content)
        h2 = compute_file_hash(content)
        assert h1 == h2

    def test_different_content_different_hash(self):
        h1 = compute_file_hash(b"Version 1")
        h2 = compute_file_hash(b"Version 2")
        assert h1 != h2

    def test_hash_is_sha256(self):
        h = compute_file_hash(b"test")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)
