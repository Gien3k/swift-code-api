# swift_api/schemas.py
import re
from typing import List, Optional, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class SwiftCodeBase(BaseModel):
    """Base schema for SWIFT code data, containing common fields."""

    # Using custom validators below instead of potentially problematic 'pattern'
    swift_code: str = Field(
        ..., min_length=8, max_length=11, description="SWIFT/BIC code"
    )
    bank_name: str = Field(..., description="Name of the bank")
    address: Optional[str] = Field(
        None, description="Address of the bank branch or HQ"
    )
    # Using custom validator below
    country_iso2: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="ISO2 country code (uppercase)",
    )
    country_name: str = Field(..., description="Country name (uppercase)")

    @field_validator("swift_code")
    @classmethod
    def check_swift_code_chars_and_length(cls, value: str) -> str:
        """Validate SWIFT code for length (8 or 11) and allowed characters (A-Z, 0-9)."""
        if not isinstance(value, str):
            raise ValueError("SWIFT code must be a string")
        if not (len(value) == 8 or len(value) == 11):
            raise ValueError("SWIFT code must be 8 or 11 characters long")
        if not re.fullmatch(r"^[A-Z0-9]+$", value):
            raise ValueError(
                "SWIFT code must contain only uppercase letters (A-Z) and digits (0-9)"
            )
        return value

    @field_validator("country_iso2")
    @classmethod
    def check_country_iso2_format(cls, value: str) -> str:
        """Validate Country ISO2 code for length (2) and allowed characters (A-Z)."""
        if not isinstance(value, str):
            raise ValueError("Country ISO2 code must be a string")
        if len(value) != 2:
            raise ValueError("Country ISO2 code must be 2 characters long")
        # Ensure uppercase check happens after potential 'before' mode conversion
        # This regex assumes the input *should* be uppercase at this point
        if not re.fullmatch(r"^[A-Z]{2}$", value):
             raise ValueError(
                 "Country ISO2 code must contain only uppercase letters (A-Z)"
             )
        return value

    # This validator runs *before* other validators for these fields
    @field_validator("country_iso2", "country_name", mode="before")
    @classmethod
    def convert_to_uppercase(cls, value: Any) -> Any:
        """Convert incoming country code and name to uppercase if they are strings."""
        if isinstance(value, str):
            return value.upper()
        return value


class SwiftCodeCreate(SwiftCodeBase):
    """Schema for creating a new SWIFT code entry via API (POST request)."""

    # is_headquarter flag is not defaulted or validated here anymore;
    # it's calculated by CRUD based on swift_code suffix.
    is_headquarter: Optional[bool] = Field(
        None,
        description=(
            "Indicates if this is a headquarter. "
            "Calculated automatically based on 'XXX' suffix during creation."
        ),
    )


class SwiftCode(SwiftCodeBase):
    """Schema representing a SWIFT code entry (used for general responses)."""

    is_headquarter: bool
    # Enable ORM mode (compatibility with SQLAlchemy models)
    model_config = ConfigDict(from_attributes=True)


class SwiftCodeBranch(BaseModel):
    """Schema representing minimal branch details (used in HQ responses)."""

    swift_code: str
    bank_name: str
    address: Optional[str] = None
    country_iso2: str
    is_headquarter: bool # Will always be False for branches listed under an HQ

    model_config = ConfigDict(from_attributes=True)


class SwiftCodeHeadquarter(SwiftCode):
    """
    Schema representing a headquarter SWIFT code entry, including its branches.
    Note: This structure is assembled in the router, not directly mapped by ORM mode alone.
    """
    branches: List[SwiftCodeBranch] = []


class SwiftCodeCountryList(BaseModel):
    """Schema for the response when listing SWIFT codes by country."""

    country_iso2: str
    country_name: str
    swift_codes: List[SwiftCode] = []


class Message(BaseModel):
    """Simple schema for success/status messages."""

    message: str

