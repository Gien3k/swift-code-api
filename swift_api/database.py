# swift_api/database.py
import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@localhost/swift_db"
)

print(f"Database URL used: {SQLALCHEMY_DATABASE_URL}") # Keep for config verification

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a SQLAlchemy database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Creates database tables based on SQLAlchemy models."""
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables checked/created successfully.") # Keep for startup feedback
    except Exception as e:
        print(f"Error creating database tables: {e}") # Keep for error reporting
