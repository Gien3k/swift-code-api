# swift_api/main.py
import os
import uvicorn # Typically needed for the `if __name__ == "__main__":` block
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict # Added for type hint

# Ensure relative imports work correctly
from . import crud, models, schemas, parser
from .database import engine, Base, get_db, init_db
from .routers import swift_codes

# Create database tables on startup (if they don't exist)
# Note: In production, migrations (e.g., Alembic) are preferred.
init_db()

# Initialize FastAPI app
app = FastAPI(
    title="SWIFT Codes API",
    description="API for managing and retrieving SWIFT/BIC codes information.",
    version="1.0.0",
)

# Include the API router defined in routers/swift_codes.py
app.include_router(
    swift_codes.router, prefix="/v1/swift-codes", tags=["SWIFT Codes"]
)


# --- Optional Data Loading Endpoint ---
@app.post(
    "/v1/load-data",
    tags=["Data Loading"],
    summary="Load SWIFT data from Excel file",
    response_model=schemas.Message,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Error loading or processing file"},
        500: {
            "description": "File path environment variable not set or other server error"
        },
    },
)
async def load_data_from_file(db: Session = Depends(get_db)) -> schemas.Message:
    """
    Loads SWIFT code data from the Excel file specified in the
    `EXCEL_FILE_PATH` environment variable (path inside the container).
    Adds new entries to the database, skipping existing ones.
    """
    # Get file path from env var or use default path inside container
    # Assumes path is relative to the WORKDIR (/app) if not absolute
    file_path_env = os.getenv("EXCEL_FILE_PATH", "data/swift_codes.xlsx")
    if not os.path.isabs(file_path_env):
         # If relative path provided in env var, join it with app root
         # WORKDIR is /app
         file_path = os.path.abspath(os.path.join("/app", file_path_env))
    else:
        file_path = file_path_env

    added_count = 0
    skipped_count = 0
    error_count = 0
    try:
        print(f"Attempting to load data from: {file_path}")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Excel file not found at resolved path: {file_path}")

        swift_data_list = parser.parse_swift_data(file_path)
        print(f"Parsed {len(swift_data_list)} records from file.")

        for swift_dict in swift_data_list:
            try:
                # Validate data using Pydantic schema before DB check
                swift_create_schema = schemas.SwiftCodeCreate(**swift_dict)

                # Check if SWIFT code already exists
                if crud.get_swift_by_code(db, swift_create_schema.swift_code):
                    skipped_count += 1
                    continue

                # Attempt to create the new entry
                if crud.create_swift(db=db, swift=swift_create_schema):
                    added_count += 1
                else:
                    # crud.create_swift returns None on IntegrityError or other DB commit errors
                    print(
                        f"Failed to add SWIFT code (likely DB issue): {swift_create_schema.swift_code}"
                    )
                    error_count += 1
            except Exception as validation_or_processing_error:
                # Catch Pydantic validation errors or other errors during iteration
                print(
                    f"Skipping record due to validation/processing error: {swift_dict.get('swift_code', 'N/A')} - {validation_or_processing_error}"
                )
                skipped_count += 1

        message = f"Data loading complete. Added: {added_count}, Skipped (existing or validation error): {skipped_count}, DB Errors: {error_count}."
        print(message)
        return schemas.Message(message=message)

    except FileNotFoundError as fnf_error:
        print(f"File not found error: {fnf_error}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(fnf_error))
    except ValueError as ve: # Catches errors from parser (e.g., missing columns)
        print(f"Value error during parsing: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing file structure or content: {ve}",
        )
    except Exception as e:
        print(f"Unexpected error during data loading: {e}")
        # TODO: Log the full error traceback here in a real application
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during data loading.", # Hide specific error from client
        )


# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def read_root() -> Dict[str, str]:
    """Provides a simple welcome message."""
    return {"message": "Welcome to the SWIFT Codes API. See /docs for details."}


# --- Allow running directly with uvicorn for local development ---
# Note: This block is not used when running with Docker via the CMD instruction
if __name__ == "__main__":
    uvicorn.run(
        "swift_api.main:app", # Reference the app object
        host="127.0.0.1",     # Listen only on localhost for direct run
        port=8080,
        reload=True          # Enable auto-reload for local development
        )
