# swift_api/routers/swift_codes.py
from typing import Any, Dict, List, Union

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

# Ensure relative imports work correctly
from .. import crud, models, schemas
from ..database import get_db

router = APIRouter()

# Reusable patterns for path parameter validation
SWIFT_CODE_PATTERN = r"^([A-Z0-9]{8}|[A-Z0-9]{11})$"
COUNTRY_CODE_PATTERN = r"^[A-Z]{2}$"


@router.get(
    "/{swift_code}",
    response_model=Union[schemas.SwiftCodeHeadquarter, schemas.SwiftCode],
    responses={
        404: {"description": "SWIFT code not found"},
        422: {"description": "Validation Error - Invalid SWIFT code format"},
        200: {
            "description": "Details of the SWIFT code",
            "content": {
                "application/json": {
                    "examples": {
                        "headquarter": {
                            "summary": "Example Headquarter Response",
                            "value": {
                                "swift_code": "BANKPLPWXXX",
                                "bank_name": "BANK POLSKA KASA OPIEKI SA",
                                "address": "GRZYBOWSKA 53/57",
                                "country_iso2": "PL",
                                "country_name": "POLAND",
                                "is_headquarter": True,
                                "branches": [
                                    {
                                        "swift_code": "PKOPPLPW123",
                                        "bank_name": "BANK POLSKA KASA OPIEKI SA",
                                        "address": "ODDZIAL",
                                        "country_iso2": "PL",
                                        "is_headquarter": False,
                                    }
                                ],
                            },
                        },
                        "branch": {
                            "summary": "Example Branch Response",
                            "value": {
                                "swift_code": "PKOPPLPW123",
                                "bank_name": "BANK POLSKA KASA OPIEKI SA",
                                "address": "ODDZIAL",
                                "country_iso2": "PL",
                                "country_name": "POLAND",
                                "is_headquarter": False,
                            },
                        },
                    }
                }
            },
        },
    },
    summary="Get details for a single SWIFT code (HQ or branch)",
)
async def read_swift_code(
    swift_code: str = Path(
        ...,
        description="The SWIFT code to retrieve (8 or 11 characters)",
        pattern=SWIFT_CODE_PATTERN,
    ),
    db: Session = Depends(get_db),
) -> Any: # Return type Any because we return dict for HQ, model for Branch
    """
    Retrieves details for a specific SWIFT code.

    - If the code represents a headquarters (ends with XXX), it also includes
      a list of associated branches.
    - If the code represents a branch, it returns only the branch details.
    """
    db_swift = crud.get_swift_by_code(db, swift_code=swift_code)
    if db_swift is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="SWIFT code not found"
        )

    if db_swift.is_headquarter:
        # Fetch branch data
        hq_prefix = db_swift.swift_code[:8]
        branches_models = crud.get_branches_by_hq_prefix(db, hq_prefix=hq_prefix)
        # Validate branches into Pydantic schemas
        branches_schemas = [
            schemas.SwiftCodeBranch.model_validate(branch) for branch in branches_models
        ]

        # Create base HQ response object and convert to dict
        hq_response_base = schemas.SwiftCode.model_validate(db_swift)
        hq_data_dict = hq_response_base.model_dump()

        # Manually add the 'branches' key with the list of branch dicts
        hq_data_dict["branches"] = [branch.model_dump() for branch in branches_schemas]

        # Return the dictionary - FastAPI will serialize it correctly
        return hq_data_dict
    else:
        # For branches, return the standard Pydantic model object
        return schemas.SwiftCode.model_validate(db_swift)


@router.get(
    "/country/{country_iso2_code}",
    response_model=schemas.SwiftCodeCountryList,
    responses={
        404: {"description": "Country ISO2 code not found in database"},
        422: {"description": "Validation Error - Invalid Country ISO2 code format"},
    },
    summary="Get all SWIFT codes for a specific country",
)
async def read_swifts_by_country(
    country_iso2_code: str = Path(
        ...,
        min_length=2,
        max_length=2,
        pattern=COUNTRY_CODE_PATTERN,
        description="The 2-letter ISO code of the country (uppercase)",
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of records to return"
    ),
    db: Session = Depends(get_db),
) -> schemas.SwiftCodeCountryList:
    """
    Retrieves a list of all SWIFT codes (headquarters and branches)
    registered for a specific country, identified by its ISO2 code.
    Supports pagination using 'skip' and 'limit' query parameters.
    """
    country_code_upper = country_iso2_code.upper()
    swift_codes_models = crud.get_swifts_by_country(
        db, country_iso2=country_code_upper, skip=skip, limit=limit
    )

    # Determine country name - needed even if swift_codes_models is empty
    # Avoid N+1: Query name only if needed or from the first result
    country_name = "Unknown"
    if swift_codes_models:
        country_name = swift_codes_models[0].country_name
    else:
        # Check if *any* record exists for this country to get the name / return 404
        any_code_for_country = (
            db.query(models.SwiftCode.country_name)
            .filter(models.SwiftCode.country_iso2 == country_code_upper)
            .first()
        )
        if any_code_for_country:
            country_name = any_code_for_country[0]
            # Country exists, but no results for this pagination window
            # Return empty list with correct country info
            return schemas.SwiftCodeCountryList(
                country_iso2=country_code_upper,
                country_name=country_name,
                swift_codes=[],
            )
        else:
            # Country code not found in the database at all
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Country ISO2 code not found in database",
            )

    # Validate the retrieved models into response schemas
    validated_codes = [
        schemas.SwiftCode.model_validate(code) for code in swift_codes_models
    ]
    return schemas.SwiftCodeCountryList(
        country_iso2=country_code_upper,
        country_name=country_name,
        swift_codes=validated_codes,
    )


@router.post(
    "/",
    response_model=schemas.Message,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "SWIFT code already exists"},
        422: {"description": "Validation Error - Invalid input data"},
    },
    summary="Add a new SWIFT code entry",
)
async def create_swift_code(
    swift_data: schemas.SwiftCodeCreate, # Input validation happens here
    db: Session = Depends(get_db),
) -> schemas.Message:
    """Adds a new SWIFT code entry to the database."""
    # Check for duplicates before attempting creation
    existing_swift = crud.get_swift_by_code(db, swift_code=swift_data.swift_code)
    if existing_swift:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SWIFT code '{swift_data.swift_code}' already exists.",
        )

    # Attempt to create the record
    created_swift = crud.create_swift(db=db, swift=swift_data)
    if created_swift is None:
        # Handle potential DB errors during create_swift commit
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Could not create SWIFT code '{swift_data.swift_code}'. "
                "Database error occurred."
            ),
        )

    return schemas.Message(
        message=f"SWIFT code '{created_swift.swift_code}' created successfully."
    )


@router.delete(
    "/{swift_code}",
    response_model=schemas.Message,
    responses={
        404: {"description": "SWIFT code not found"},
        422: {"description": "Validation Error - Invalid SWIFT code format"},
    },
    summary="Delete a SWIFT code entry",
)
async def delete_swift_code(
    swift_code: str = Path(
        ..., description="The SWIFT code to delete", pattern=SWIFT_CODE_PATTERN
    ),
    db: Session = Depends(get_db),
) -> schemas.Message:
    """Deletes a SWIFT code entry from the database based on its code."""
    deleted_swift = crud.delete_swift(db, swift_code=swift_code)
    if deleted_swift is None:
        # Handles both "not found" and potential DB errors during delete
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="SWIFT code not found or error during deletion."
        )
    return schemas.Message(
        message=f"SWIFT code '{swift_code.upper()}' deleted successfully."
    )
