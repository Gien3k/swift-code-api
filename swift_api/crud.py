# swift_api/crud.py
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

# Make sure imports work correctly relative to the execution context
from . import models, schemas


def get_swift_by_code(db: Session, swift_code: str) -> Optional[models.SwiftCode]:
    """Retrieves a single SWIFT entry based on its code."""
    return (
        db.query(models.SwiftCode)
        .filter(models.SwiftCode.swift_code == swift_code.upper())
        .first()
    )


def get_swifts_by_country(
    db: Session, country_iso2: str, skip: int = 0, limit: int = 100
) -> List[models.SwiftCode]:
    """Retrieves a list of SWIFT entries for a given country with pagination."""
    return (
        db.query(models.SwiftCode)
        .filter(models.SwiftCode.country_iso2 == country_iso2.upper())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_branches_by_hq_prefix(db: Session, hq_prefix: str) -> List[models.SwiftCode]:
    """Retrieves a list of branches (non-HQ) matching the 8-char HQ prefix."""
    if len(hq_prefix) != 8:
        return []
    return (
        db.query(models.SwiftCode)
        .filter(
            models.SwiftCode.swift_code.startswith(hq_prefix.upper()),
            models.SwiftCode.is_headquarter == False,
        )
        .all()
    )


def create_swift(
    db: Session, swift: schemas.SwiftCodeCreate
) -> Optional[models.SwiftCode]:
    """Creates a new SWIFT entry in the database."""

    # Always calculate is_hq based on the swift code suffix, ignore value from schema
    is_hq = swift.swift_code.upper().endswith("XXX")

    db_swift = models.SwiftCode(
        swift_code=swift.swift_code.upper(),
        bank_name=swift.bank_name,
        address=swift.address,
        country_iso2=swift.country_iso2.upper(),
        country_name=swift.country_name.upper(),
        is_headquarter=is_hq,
    )
    db.add(db_swift)
    try:
        db.commit()
        db.refresh(db_swift)
        return db_swift
    except IntegrityError:  # Handle primary key violation (duplicate)
        db.rollback()
        # Optionally log this error in a real application
        return None
    except Exception as e:  # Handle other potential DB errors
        # Optionally log this error in a real application
        print(f"Error during DB commit/refresh for {swift.swift_code}: {e}") # Keep basic error print for now
        db.rollback()
        return None


def delete_swift(db: Session, swift_code: str) -> Optional[models.SwiftCode]:
    """Deletes a SWIFT entry from the database based on its code."""
    db_swift = get_swift_by_code(db, swift_code) # Uses .upper() inside
    if db_swift:
        try:
            db.delete(db_swift)
            db.commit()
            return db_swift
        except Exception as e:
            # Optionally log this error in a real application
            print(f"Error during DB delete/commit for {swift_code}: {e}") # Keep basic error print for now
            db.rollback()
            # Return None if deletion fails
            return None
    # Return None if code was not found
    return None
