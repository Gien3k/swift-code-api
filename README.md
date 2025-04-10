# SWIFT Codes API
[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Framework: FastAPI](https://img.shields.io/badge/framework-FastAPI-05998b)](https://fastapi.tiangolo.com/)
[![Run Python Tests](https://github.com/Gien3k/swift-code-api/actions/workflows/ci.yml/badge.svg)](https://github.com/Gien3k/swift-code-api/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

This project provides a RESTful API service for managing and retrieving SWIFT/BIC (Bank Identifier Code) information. **The source data (SWIFT codes in Excel format) for this exercise was provided by Remitly.** It is designed to parse data from the spreadsheet, process it according to specified rules (identifying headquarters vs. branches, ensuring data format consistency), store it efficiently in a PostgreSQL database optimized for fast querying, and expose the data through a clean, containerized FastAPI application.


## Features

* **Excel Data Parsing:** Parses SWIFT code data from a `.xlsx` file using Pandas.
* **Code Identification & Association:**
    * Identifies headquarters codes (ending in "XXX") and branch codes.
    * Correctly associates branch codes with their corresponding headquarters based on the first 8 characters of the SWIFT code (logic implemented in API responses).
* **Data Formatting:** Ensures country codes (ISO2) and country names are consistently stored and returned in uppercase.
* **Database Storage:** Utilizes PostgreSQL within a Docker container for persistent storage, with SQLAlchemy as the ORM.
* **RESTful API:** Exposes data via a FastAPI application with the following endpoints:
    * `GET /v1/swift-codes/{swift_code}`: Retrieve details for a single SWIFT code. HQ responses include a list of associated branches.
    * `GET /v1/swift-codes/country/{countryISO2code}`: Retrieve all SWIFT codes for a specific country (using 2-letter uppercase ISO code). Supports pagination.
    * `POST /v1/swift-codes/`: Add a new SWIFT code entry to the database.
    * `DELETE /v1/swift-codes/{swift-code}`: Delete a specific SWIFT code entry.
* **Data Loading:** Includes a `POST /v1/load-data` endpoint to easily populate the database from the source Excel file.
* **Containerization:** Fully containerized using Docker and Docker Compose for straightforward setup, dependency management, and deployment consistency. The API is accessible on `http://localhost:8080`.
* **Automated Tests:** Includes a suite of unit and integration tests written with `pytest` to ensure code correctness and reliability.

## Technology Stack

* **Language:** Python 3.11
* **API Framework:** FastAPI
* **Web Server:** Uvicorn
* **Database:** PostgreSQL (via Docker)
* **ORM:** SQLAlchemy
* **Data Parsing:** Pandas, openpyxl
* **Data Validation:** Pydantic
* **Containerization:** Docker, Docker Compose
* **Testing:** Pytest, HTTPX, TestClient

## Prerequisites

Ensure you have the following installed on your system:

* **Docker:** [Install Docker](https://docs.docker.com/get-docker/)
* **Docker Compose:** Typically included with Docker Desktop. (Check installation: `docker compose version`)
* **(Optional) Git:** For cloning the repository.

## Setup and Configuration

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/Gien3k/swift-code-api.git
    cd swift-code-api
    ```

2.  **Configure Environment Variables:**
    * Copy the example environment file to create your local configuration:
        ```bash
        cp .env.example .env
        ```
    * **Edit the `.env` file.** Review the default values and **set a secure `POSTGRES_PASSWORD`**. Ensure `EXCEL_FILE_PATH` points to the location of your data file *relative to the project root* (default is `data/swift_codes.xlsx`).

3.  **Place Input Data File:**
    * Create the `data` directory if it doesn't exist: `mkdir data`
    * Place your SWIFT codes Excel file (e.g., `swift_codes.xlsx`) inside the `data/` directory. The filename must match the one specified by `EXCEL_FILE_PATH` in your `.env` file (or the default).

## Running the Application

1.  **Build and Start Services:** From the project root directory, run:
    ```bash
    docker-compose up --build -d
    ```
    * `--build`: Ensures the application Docker image is built (or rebuilt if code changes).
    * `-d`: Runs the containers in detached mode (background).
    * This command starts the PostgreSQL database container (`db`) and the FastAPI application container (`app`).

2.  **Check Status:** Verify that both containers are running:
    ```bash
    docker-compose ps
    ```
    * Look for the `app` and `db` services with an `Up` or `running` status. The `db` service should also show `(healthy)` after a short time.

3.  **Access API:** The API should now be running and accessible at `http://localhost:8080`.

## Loading Initial Data

The database starts empty upon the first run. To populate it using the data from your Excel file:

1.  Make sure the containers are running (`docker-compose up -d`).
2.  Execute the following command in your terminal:
    ```bash
    curl -X POST http://localhost:8080/v1/load-data
    ```
3.  A successful response will look like:
    ```json
    {"message":"Data loading complete. Added: <N>, Skipped (existing or validation error): <M>, DB Errors: <Z>."}
    ```
    *(Check `docker-compose logs app` for details or errors during loading).*

## API Usage

### Interactive Documentation

Interactive API documentation (provided by FastAPI/Swagger UI and ReDoc) is available at:

* **Swagger UI:** `http://localhost:8080/docs`
* **ReDoc:** `http://localhost:8080/redoc`

These interfaces allow easy exploration and testing of the endpoints directly from your browser.

### Endpoints Summary

*(Replace placeholders like `{swift-code}` and `{countryISO2code}` with actual values)*

* **`GET /v1/swift-codes/{swift-code}`**: Retrieves details for a specific SWIFT code.
    * *Example:* `curl http://localhost:8080/v1/swift-codes/TESTHQ01XXX`
    * *HQ Example:* `curl http://localhost:8080/v1/swift-codes/APIHQ123XXX` (Response includes `branches` list)

* **`GET /v1/swift-codes/country/{countryISO2code}`**: Retrieves all SWIFT codes for a specific country (case-insensitive ISO2 code). Supports pagination.
    * *Example:* `curl http://localhost:8080/v1/swift-codes/country/PL | jq`
    * *Example (Pagination):* `curl http://localhost:8080/v1/swift-codes/country/DE?skip=5&limit=10`

* **`POST /v1/swift-codes/`**: Adds a new SWIFT code entry. Requires a JSON body.
    * *Example:*
        ```bash
        curl -X POST -H "Content-Type: application/json" \
        -d '{"swift_code": "NEWBANKDE", "bank_name": "My New German Bank", "address": "1 Berlin St", "country_iso2": "DE", "country_name": "GERMANY"}' \
        http://localhost:8080/v1/swift-codes/
        ```
        *(Returns `{"message": "SWIFT code 'NEWBANKDE' created successfully."}`)*

* **`DELETE /v1/swift-codes/{swift-code}`**: Deletes a specific SWIFT code entry.
    * *Example:* `curl -X DELETE http://localhost:8080/v1/swift-codes/NEWBANKDE`
    * *(Returns `{"message": "SWIFT code 'NEWBANKDE' deleted successfully."}`)*

## Running Tests

Automated tests are included using `pytest`.

1.  Ensure the application and database containers are running:
    ```bash
    docker-compose up -d
    ```
2.  Execute the tests within the `app` container:
    ```bash
    docker-compose exec app pytest -v
    ```
    * Tests run against a separate, temporary SQLite database for isolation.

## Stopping the Application

To stop and remove the containers, network, and optionally the database volume:

```bash
# Stop and remove containers & network
docker-compose down

# Stop and remove containers, network, AND the database volume (data loss!)
docker-compose down -v
```
