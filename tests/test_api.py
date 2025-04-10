# tests/test_api.py
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Assumes imports work correctly from the project root (/app in container)
from swift_api import crud, schemas

# --- Test Data Constants (Corrected) ---
HQ_CODE = "APIHQ123XXX"  
BRANCH_CODE_1 = "APIHQ123B01"  
BRANCH_CODE_2 = "APIHQ123B02"  
OTHER_BRANCH = "APIBRANC"  
COUNTRY_ISO = "AP"
COUNTRY_NAME = "APILAND"


@pytest.fixture(scope="function", autouse=True)
def setup_db_for_api_tests(db_session: Session):
    """
    Auto-used fixture to populate the test database with standard data
    before each API test function runs.
    """
    crud.create_swift(
        db=db_session,
        swift=schemas.SwiftCodeCreate(
            swift_code=HQ_CODE,
            bank_name="API HQ Bank",
            address="1 API Street",
            country_iso2=COUNTRY_ISO,
            country_name=COUNTRY_NAME,
        ),
    )
    crud.create_swift(
        db=db_session,
        swift=schemas.SwiftCodeCreate(
            swift_code=BRANCH_CODE_1,
            bank_name="API Branch 1",
            address="1a Branch Ave",
            country_iso2=COUNTRY_ISO,
            country_name=COUNTRY_NAME,
            is_headquarter=False,
        ),
    )
    crud.create_swift(
        db=db_session,
        swift=schemas.SwiftCodeCreate(
            swift_code=BRANCH_CODE_2,
            bank_name="API Branch 2",
            address="1b Branch Ave",
            country_iso2=COUNTRY_ISO,
            country_name=COUNTRY_NAME,
            is_headquarter=False,
        ),
    )
    crud.create_swift(
        db=db_session,
        swift=schemas.SwiftCodeCreate(
            swift_code=OTHER_BRANCH,
            bank_name="API Other Branch",
            address="2 Other Road",
            country_iso2=COUNTRY_ISO,
            country_name=COUNTRY_NAME,
            is_headquarter=False,
        ),
    )

# --- API Endpoint Tests ---


def test_read_root(client: TestClient):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "message": "Welcome to the SWIFT Codes API. See /docs for details."
    }


def test_read_swift_code_hq(client: TestClient):
    """Test retrieving details for a headquarter code, expecting branches."""
    response = client.get(f"/v1/swift-codes/{HQ_CODE}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["swift_code"] == HQ_CODE
    assert data["is_headquarter"] is True
    assert "branches" in data
    assert isinstance(data["branches"], list)
    assert len(data["branches"]) == 2
    branch_codes = {b["swift_code"] for b in data["branches"]}
    assert BRANCH_CODE_1 in branch_codes
    assert BRANCH_CODE_2 in branch_codes
    for branch in data["branches"]:
        assert branch["is_headquarter"] is False


def test_read_swift_code_branch(client: TestClient):
    """Test retrieving details for a branch code, expecting no branches key."""
    response = client.get(f"/v1/swift-codes/{BRANCH_CODE_1}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["swift_code"] == BRANCH_CODE_1
    assert data["is_headquarter"] is False
    assert "branches" not in data


def test_read_swift_code_not_found(client: TestClient):
    """Test retrieving a non-existent SWIFT code."""
    response = client.get("/v1/swift-codes/NONEXIST")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "SWIFT code not found"


def test_read_swifts_by_country(client: TestClient):
    """Test retrieving all SWIFT codes for a specific country."""
    response = client.get(f"/v1/swift-codes/country/{COUNTRY_ISO}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["country_iso2"] == COUNTRY_ISO
    assert data["country_name"] == COUNTRY_NAME
    assert isinstance(data["swift_codes"], list)
    assert len(data["swift_codes"]) == 4
    swift_codes_in_response = {s["swift_code"] for s in data["swift_codes"]}
    assert HQ_CODE in swift_codes_in_response
    assert BRANCH_CODE_1 in swift_codes_in_response
    assert BRANCH_CODE_2 in swift_codes_in_response
    assert OTHER_BRANCH in swift_codes_in_response


def test_read_swifts_by_country_not_found(client: TestClient):
    """Test retrieving SWIFT codes for a non-existent country code."""
    response = client.get("/v1/swift-codes/country/XX")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Country ISO2 code not found in database"


def test_create_swift_code_success(client: TestClient):
    """Test successfully creating a new SWIFT code."""
    new_swift_data = {
        "swift_code": "NEWCODE1", 
        "bank_name": "New Test Bank",
        "address": "1 New Street",
        "country_iso2": "NW",
        "country_name": "Newland",
        "is_headquarter": False,
    }
    response = client.post("/v1/swift-codes/", json=new_swift_data)
    assert response.status_code == status.HTTP_201_CREATED
    assert (
        response.json()["message"]
        == f"SWIFT code '{new_swift_data['swift_code']}' created successfully."
    )

    get_response = client.get(f"/v1/swift-codes/{new_swift_data['swift_code']}")
    assert get_response.status_code == status.HTTP_200_OK
    assert get_response.json()["bank_name"] == "New Test Bank"


def test_create_swift_code_duplicate(client: TestClient):
    """Test attempting to create a SWIFT code that already exists."""
    duplicate_swift_data = {
        "swift_code": HQ_CODE,
        "bank_name": "Trying Duplicate",
        "country_iso2": COUNTRY_ISO,
        "country_name": COUNTRY_NAME,
    }
    response = client.post("/v1/swift-codes/", json=duplicate_swift_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert f"SWIFT code '{HQ_CODE}' already exists" in response.json()["detail"]


def test_create_swift_code_invalid_data_validation(client: TestClient):
    """Test creating a SWIFT code with invalid input data (validation error)."""
    invalid_swift_data = {
        "swift_code": "INVLD",  # Too short
        "bank_name": "Invalid Bank",
        "country_iso2": "IV", # Valid ISO2 format, but not necessarily a real country
        "country_name": "Invalidland",
    }
    response = client.post("/v1/swift-codes/", json=invalid_swift_data)
    # Expecting validation error because 'swift_code' is too short
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_delete_swift_code_success(client: TestClient):
    """Test successfully deleting an existing SWIFT code."""
    code_to_delete = OTHER_BRANCH
    # Ensure the code exists before attempting delete
    get_resp_before = client.get(f"/v1/swift-codes/{code_to_delete}")
    if get_resp_before.status_code != status.HTTP_200_OK:
        pytest.fail(
            f"Setup failed: Could not find {code_to_delete} before delete test."
            f" Error: {get_resp_before.text}"
        )

    response = client.delete(f"/v1/swift-codes/{code_to_delete}")
    assert response.status_code == status.HTTP_200_OK
    assert (
        response.json()["message"]
        == f"SWIFT code '{code_to_delete}' deleted successfully."
    )

    # Verify it's gone
    assert (
        client.get(f"/v1/swift-codes/{code_to_delete}").status_code
        == status.HTTP_404_NOT_FOUND
    )


def test_delete_swift_code_not_found(client: TestClient):
    """Test attempting to delete a non-existent SWIFT code."""
    response = client.delete("/v1/swift-codes/NONEXIST")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    # --- POPRAWKA TUTAJ: Oczekiwany komunikat błędu ---
    assert response.json()["detail"] == "SWIFT code not found or error during deletion."


def test_read_swift_code_invalid_format(client: TestClient):
    """Test retrieving SWIFT codes with invalid format in the path."""
    invalid_codes = ["SHORT", "TOOLONGCODE12", "INV@LID"]
    for code in invalid_codes:
        response = client.get(f"/v1/swift-codes/{code}")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_read_swifts_by_country_pagination(client: TestClient):
    """Test pagination for retrieving SWIFT codes by country."""
    # Assumes setup fixture added 4 codes for country 'AP'
    response1 = client.get(f"/v1/swift-codes/country/AP?skip=0&limit=2")
    assert response1.status_code == status.HTTP_200_OK
    assert len(response1.json()["swift_codes"]) == 2

    response2 = client.get(f"/v1/swift-codes/country/AP?skip=2&limit=2")
    assert response2.status_code == status.HTTP_200_OK
    assert len(response2.json()["swift_codes"]) == 2

    response3 = client.get(f"/v1/swift-codes/country/AP?skip=4&limit=2")
    assert response3.status_code == status.HTTP_200_OK
    assert len(response3.json()["swift_codes"]) == 0

    # Test invalid pagination parameters (negative skip should fail validation)
    response_err = client.get(f"/v1/swift-codes/country/AP?skip=-1&limit=10")
    assert response_err.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
