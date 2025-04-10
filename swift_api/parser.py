# swift_api/parser.py
import os
from typing import Any, Dict, List

import pandas as pd

# Define expected Excel column names and their mapping to internal field names
# Ensure keys exactly match the column headers in the source Excel file
COLUMN_MAPPING = {
    "COUNTRY ISO2 CODE": "country_iso2",
    "SWIFT CODE": "swift_code",
    "NAME": "bank_name",
    "ADDRESS": "address",
    "COUNTRY NAME": "country_name",
}

# List of column names required to be present in the Excel file
REQUIRED_COLUMNS = list(COLUMN_MAPPING.keys())


def parse_swift_data(file_path: str) -> List[Dict[str, Any]]:
    """
    Parses the SWIFT data from the specified Excel file.

    Args:
        file_path: The absolute or relative path to the Excel file.

    Returns:
        A list of dictionaries, where each dictionary represents a row
        with cleaned and validated SWIFT code data, ready for processing
        (e.g., creating Pydantic models or database entries).

    Raises:
        FileNotFoundError: If the specified file_path does not exist.
        ValueError: If any required columns are missing from the Excel file.
        Exception: Propagates other exceptions during file processing (e.g., pandas errors).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Source Excel file not found at: {file_path}")

    try:
        # Read the first sheet from the Excel file
        df = pd.read_excel(file_path, sheet_name=0, engine="openpyxl")

        # Verify that all required columns exist
        missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise ValueError(
                f"Missing required columns in Excel file: {', '.join(missing_cols)}"
            )

        # Select only the required columns
        df = df[REQUIRED_COLUMNS]

        # Rename columns to match internal field names
        df.rename(columns=COLUMN_MAPPING, inplace=True)

        # --- Data Cleaning and Formatting ---

        # Fill missing values (NaN) with empty strings first
        df = df.fillna("")

        # Then convert columns to string type and apply case changes
        df["swift_code"] = df["swift_code"].astype(str).str.upper()
        df["country_iso2"] = df["country_iso2"].astype(str).str.upper()
        df["country_name"] = df["country_name"].astype(str).str.upper()
        df["bank_name"] = df["bank_name"].astype(str)
        df["address"] = df["address"].astype(str) # Now converts '' to ''

        # Determine the 'is_headquarter' flag based on 'XXX' suffix
        df["is_headquarter"] = df["swift_code"].str.endswith("XXX")

        # --- Basic Data Validation ---

        # Drop rows where essential data might still be missing after fillna/astype
        # (though fillna('') should prevent NaNs)
        df.dropna(
            subset=["swift_code", "country_iso2", "country_name", "bank_name"],
            inplace=True,
        )
        # Filter based on valid SWIFT code length (8 or 11)
        df = df[df["swift_code"].str.len().isin([8, 11])]
        # Filter based on valid country ISO2 code length
        df = df[df["country_iso2"].str.len() == 2]
        # Remove rows where essential fields became empty strings after cleaning
        df = df[df["swift_code"] != ""]
        df = df[df["country_iso2"] != ""]
        df = df[df["country_name"] != ""]
        df = df[df["bank_name"] != ""]

        # Convert the cleaned DataFrame to a list of dictionaries
        records = df.to_dict(orient="records")

        return records

    except Exception as e:
        # Log and re-raise other potential errors during parsing
        print(f"Error parsing Excel file '{file_path}': {e}") # Keep basic error logging
        raise e
