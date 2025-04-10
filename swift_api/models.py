# swift_api/models.py

from sqlalchemy import Boolean, Column, Index, String

# Import Base from the database setup file
from .database import Base


class SwiftCode(Base):
    """SQLAlchemy model representing a SWIFT code entry in the database."""

    __tablename__ = "swift_codes"

    # Column definitions
    swift_code = Column(String, primary_key=True, index=True)
    bank_name = Column(String, nullable=False)
    address = Column(String, nullable=True) # Address can be optional/empty
    # index=True automatically creates an index on this column
    country_iso2 = Column(String(2), nullable=False, index=True)
    country_name = Column(String, nullable=False)
    is_headquarter = Column(Boolean, nullable=False, default=False)

    # __table_args__ for explicit index removed as index=True is sufficient

    def __repr__(self) -> str:
        """String representation of the SwiftCode object (useful for debugging)."""
        return f"<SwiftCode(swift_code='{self.swift_code}', bank_name='{self.bank_name}', country='{self.country_iso2}')>"
