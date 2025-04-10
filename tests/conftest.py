# tests/conftest.py
import os
import pytest
from typing import Generator, Any

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Ensure imports from the application work correctly
# Assumes pytest is run from the project root (/app in container)
from swift_api.database import Base
from swift_api.main import app  # Import the FastAPI application instance
from swift_api.database import get_db  # Import the original DB dependency


# --- Test Database Setup ---

# Use a separate SQLite database file for tests
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///./test_swift_api.db"

# Remove the test database file before tests run, if it exists
if os.path.exists("./test_swift_api.db"):
    print(f"Removing existing test database: {TEST_SQLALCHEMY_DATABASE_URL}")
    try:
        os.remove("./test_swift_api.db")
    except OSError as e:
        print(f"Error removing test database file: {e}")


# Create SQLAlchemy engine for the test database
# connect_args is required for SQLite with multi-threaded access (like FastAPI/Starlette)
engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create a sessionmaker for the test database
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Create tables in the test database *before* the test session starts
try:
    Base.metadata.create_all(bind=engine)
    print("Test database tables created.")
except Exception as e:
    print(f"Error creating test database tables: {e}")
    # Depending on severity, you might want to raise the exception
    # raise


# --- Dependency Override ---

def override_get_db() -> Generator[Session, None, None]:
    """Dependency override for get_db that yields a test database session."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Apply the dependency override to the FastAPI app instance
# All API tests using the 'client' fixture will now use the test database
app.dependency_overrides[get_db] = override_get_db


# --- Pytest Fixtures ---

@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Pytest fixture providing a SQLAlchemy Session for database operations.
    Cleans up the database tables after each test function.
    """
    session = TestingSessionLocal()
    try:
        yield session
        # Commit any changes made *if* the test function completed successfully
        # (Tests often shouldn't rely on this commit, but perform their own)
        # session.commit()
    except Exception:
        # Rollback in case of test errors
        session.rollback()
        raise
    finally:
        # Clean up: Delete all data from tables after each test
        print("Cleaning up test database tables...")
        for table in reversed(Base.metadata.sorted_tables):
            try:
                session.execute(table.delete())
                session.commit() # Commit the delete for each table
            except Exception as e:
                print(f"Error cleaning table {table.name}: {e}")
                session.rollback()
        session.close()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """
    Pytest fixture providing a FastAPI TestClient instance
    configured to use the test database.
    Scope is 'module' for efficiency if client setup is expensive.
    """
    # TestClient uses the 'app' instance where get_db has been overridden
    with TestClient(app) as test_client:
        yield test_client
