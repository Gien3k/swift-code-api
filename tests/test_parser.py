# tests/test_parser.py
import os
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pytest

# Assuming swift_api is importable from the project root (/app in container)
from swift_api.parser import COLUMN_MAPPING, parse_swift_data


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Provides a sample Pandas DataFrame simulating raw Excel data."""
    data = {
        "COUNTRY ISO2 CODE": ["PL", "DE", "US", "BE", "FR"],
        "SWIFT CODE": ["BANKPLPWXXX", "BANKDEFF", "CITIUS33", "INVBEBBE", "INVALID"],
        "CODE TYPE": ["BC11", "BC11", "BC11", "BC11", "BC11"],
        "NAME": [
            "Bank Polski",
            "Deutsche Bank",
            "Citibank NA",
            "INVEST BANK",
            "Invalid Bank",
        ],
        "ADDRESS": ["Warsaw", "Frankfurt", "New York", "", None],
        "TOWN NAME": ["WARSZAWA", "FRANKFURT", "NEW YORK", "BRUSSELS", "PARIS"],
        "COUNTRY NAME": ["poland", "GERMANY", "united states", "Belgium", "France"],
        "TIME ZONE": [
            "Europe/Warsaw",
            "Europe/Berlin",
            "America/New_York",
            "Europe/Brussels",
            "Europe/Paris",
        ],
        "EXTRA COLUMN": ["ignore", "this", "data", "please", "test"],
    }
    return pd.DataFrame(data)


@pytest.fixture
def temp_excel_file(sample_dataframe: pd.DataFrame, tmp_path: Path) -> str:
    """Creates a temporary Excel file from the sample_dataframe fixture."""
    file_path = tmp_path / "temp_swift_data.xlsx"
    sample_dataframe.to_excel(file_path, index=False, engine="openpyxl")
    return str(file_path)


def test_parse_swift_data_success(temp_excel_file: str):
    """Tests successful parsing of a valid Excel file."""
    parsed_data = parse_swift_data(temp_excel_file)
    assert len(parsed_data) == 4 # Expect 4 valid records
    assert parsed_data[0]["swift_code"] == "BANKPLPWXXX"
    assert parsed_data[0]["country_iso2"] == "PL"
    assert parsed_data[0]["country_name"] == "POLAND"
    assert parsed_data[0]["is_headquarter"] is True
    assert parsed_data[1]["swift_code"] == "BANKDEFF"
    assert parsed_data[1]["country_iso2"] == "DE"
    assert parsed_data[1]["is_headquarter"] is False
    assert parsed_data[3]["swift_code"] == "INVBEBBE"
    assert parsed_data[3]["address"] == ""
    assert parsed_data[3]["is_headquarter"] is False


def test_parse_swift_data_file_not_found():
    """Tests the error handling when the source file does not exist."""
    with pytest.raises(FileNotFoundError):
        parse_swift_data("non_existent_file.xlsx")


def test_parse_swift_data_missing_column(tmp_path: Path):
    """Tests the error handling when a required column is missing."""
    data = {"COUNTRY ISO2 CODE": ["PL"], "NAME": ["Bank Polski"]} # Missing other required keys
    df = pd.DataFrame(data)
    file_path = tmp_path / "missing_col.xlsx"
    df.to_excel(file_path, index=False, engine="openpyxl")

    # Expect ValueError mentioning the missing columns with the English message
    # --- POPRAWKA TUTAJ: Oczekiwany komunikat błędu ---
    with pytest.raises(ValueError, match="Missing required columns"):
        try:
            parse_swift_data(str(file_path))
        except ValueError as e:
            error_message = str(e)
            assert "SWIFT CODE" in error_message
            assert "COUNTRY NAME" in error_message
            assert "ADDRESS" in error_message
            raise e # Re-raise to satisfy pytest.raises
