from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path

from backend.config import settings, BASE_DIR

db_url = settings.database_url
if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////"):
    rel = db_url.replace("sqlite:///", "").lstrip("./")
    abs_path = (BASE_DIR / rel).resolve()
    db_url = f"sqlite:///{abs_path}"

db_path = db_url.replace("sqlite:///", "")
Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    db_url,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from backend import models  # Ensure all model tables are registered in Base.metadata
    Base.metadata.create_all(bind=engine)

