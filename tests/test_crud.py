# tests/test_crud.py
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

# Ensure imports work correctly from the project root (/app in container)
from swift_api import crud, models, schemas

# Use the db_session fixture defined in conftest.py


@pytest.fixture(scope="function", autouse=True)
def setup_and_teardown_db(db_session: Session):
    """Ensures a clean database state before each test via db_session fixture."""
    # Cleanup is handled by the db_session fixture in conftest.py
    yield
    # Teardown (cleanup) happens in db_session.finally


def test_create_swift_hq(db_session: Session):
    """Tests creating a headquarter (HQ) entry."""
    hq_data = schemas.SwiftCodeCreate(
        swift_code="TESTHQ01XXX",
        bank_name="Test Bank HQ",
        address="1 Test Street",
        country_iso2="TS",
        country_name="Testland",
    )
    db_swift = crud.create_swift(db=db_session, swift=hq_data)
    assert db_swift is not None
    assert db_swift.swift_code == "TESTHQ01XXX"
    assert db_swift.is_headquarter is True
    assert db_swift.country_name == "TESTLAND"


def test_create_swift_branch(db_session: Session):
    """Tests creating a branch entry."""
    branch_data = schemas.SwiftCodeCreate(
        swift_code="TESTBRC1",
        bank_name="Test Bank Branch",
        address="2 Branch Road",
        country_iso2="TS",
        country_name="Testland",
        is_headquarter=False,
    )
    db_swift = crud.create_swift(db=db_session, swift=branch_data)
    assert db_swift is not None
    assert db_swift.swift_code == "TESTBRC1"
    assert db_swift.is_headquarter is False


def test_get_swift_by_code(db_session: Session):
    """Tests retrieving an entry by SWIFT code."""
    hq_data = schemas.SwiftCodeCreate(
        swift_code="GETBYCD1XXX",
        bank_name="Get Bank",
        country_iso2="GB",
        country_name="Getland",
    )
    crud.create_swift(db=db_session, swift=hq_data)

    # Test retrieving existing code
    fetched_swift = crud.get_swift_by_code(db=db_session, swift_code="GETBYCD1XXX")
    assert fetched_swift is not None
    assert fetched_swift.bank_name == "Get Bank"

    # Test retrieving non-existent code
    not_found_swift = crud.get_swift_by_code(db=db_session, swift_code="NONEXIST")
    assert not_found_swift is None


def test_get_swifts_by_country(db_session: Session):
    """Tests retrieving entries by country code."""
    country_code_1 = "CC"
    country_code_2 = "DD"
    swift_1_hq = "COUNTRY1XXX"
    swift_1_br = "BRANCH01"
    swift_2_hq = "CNTRY2HQ"

    crud.create_swift(
        db=db_session,
        swift=schemas.SwiftCodeCreate(
            swift_code=swift_1_hq,
            bank_name="C1 Bank",
            country_iso2=country_code_1,
            country_name="CountryOne",
        ),
    )
    crud.create_swift(
        db=db_session,
        swift=schemas.SwiftCodeCreate(
            swift_code=swift_1_br,
            bank_name="C1 Branch",
            country_iso2=country_code_1,
            country_name="CountryOne",
        ),
    )
    crud.create_swift(
        db=db_session,
        swift=schemas.SwiftCodeCreate(
            swift_code=swift_2_hq,
            bank_name="C2 Bank",
            country_iso2=country_code_2,
            country_name="CountryTwo",
        ),
    )

    # Query for the first country code ("CC")
    c1_swifts = crud.get_swifts_by_country(db=db_session, country_iso2=country_code_1)
    assert len(c1_swifts) == 2

    # Query for the second country code (case-insensitive check)
    c2_swifts = crud.get_swifts_by_country(
        db=db_session, country_iso2=country_code_2.lower()
    )
    assert len(c2_swifts) == 1
    assert c2_swifts[0].swift_code == swift_2_hq

    # Query for a non-existent country code
    c3_swifts = crud.get_swifts_by_country(db=db_session, country_iso2="XX")
    assert len(c3_swifts) == 0


def test_get_branches_by_hq_prefix(db_session: Session):
    """Tests retrieving branches for a given HQ prefix."""
    prefix = "TESTPREF"
    hq_code = f"{prefix}XXX"
    branch1_code = f"{prefix}B01"
    branch2_code = f"{prefix}B02"
    other_hq_code = "PASSINGHQ01"
    other_branch_code = "ANOTHERH"

    crud.create_swift(
        db=db_session,
        swift=schemas.SwiftCodeCreate(
            swift_code=hq_code, bank_name="HQ", country_iso2="BR", country_name="Branchland"
        ),
    )
    crud.create_swift(
        db=db_session,
        swift=schemas.SwiftCodeCreate(
            swift_code=branch1_code,
            bank_name="B1",
            country_iso2="BR",
            country_name="Branchland",
            is_headquarter=False,
        ),
    )
    crud.create_swift(
        db=db_session,
        swift=schemas.SwiftCodeCreate(
            swift_code=branch2_code,
            bank_name="B2",
            country_iso2="BR",
            country_name="Branchland",
            is_headquarter=False,
        ),
    )
    crud.create_swift(
        db=db_session,
        swift=schemas.SwiftCodeCreate(
            swift_code=other_hq_code,
            bank_name="Other HQ",
            country_iso2="OT",
            country_name="Otherland",
        ),
    )
    crud.create_swift(
        db=db_session,
        swift=schemas.SwiftCodeCreate(
            swift_code=other_branch_code,
            bank_name="Other B1",
            country_iso2="OT",
            country_name="Otherland",
            is_headquarter=False,
        ),
    )

    branches = crud.get_branches_by_hq_prefix(db=db_session, hq_prefix=prefix)
    assert len(branches) == 2
    branch_codes_fetched = {b.swift_code for b in branches}
    assert branch1_code in branch_codes_fetched
    assert branch2_code in branch_codes_fetched


def test_delete_swift(db_session: Session):
    """Tests deleting an entry."""
    swift_to_delete = "DELETE01"
    crud.create_swift(
        db=db_session,
        swift=schemas.SwiftCodeCreate(
            swift_code=swift_to_delete,
            bank_name="Delete Bank",
            country_iso2="DL",
            country_name="Deleteland",
        ),
    )
    # Verify it exists before delete
    assert crud.get_swift_by_code(db=db_session, swift_code=swift_to_delete) is not None

    # Perform delete
    deleted = crud.delete_swift(db=db_session, swift_code=swift_to_delete)
    assert deleted is not None
    assert deleted.swift_code == swift_to_delete

    # Verify it's gone
    assert crud.get_swift_by_code(db=db_session, swift_code=swift_to_delete) is None

    # Test deleting non-existent code
    not_deleted = crud.delete_swift(db=db_session, swift_code="NONEXIST")
    assert not_deleted is None


# Filter the specific SQLAlchemy warning about conflicting instances for this test
@pytest.mark.filterwarnings("ignore::sqlalchemy.exc.SAWarning")
def test_create_swift_duplicate(db_session: Session):
    """Tests attempting to add a duplicate SWIFT code."""
    swift_code = "DUPLICATEXX"  
    initial_data = schemas.SwiftCodeCreate(
        swift_code=swift_code,
        bank_name="Original Dup Bank",
        country_iso2="DP",
        country_name="Dupland",
    )
    # Add the first instance
    created = crud.create_swift(db=db_session, swift=initial_data)
    assert created is not None

    # Attempt to add the same code again
    duplicate_data = schemas.SwiftCodeCreate(
        swift_code=swift_code,
        bank_name="Dup Bank Again",
        country_iso2="DP",
        country_name="Dupland",
    )
    # Expect crud.create_swift to handle IntegrityError and return None
    assert crud.create_swift(db=db_session, swift=duplicate_data) is None
