# Use an official lightweight Python image
FROM python:3.11-slim

# Set environment variables
# Prevents Python output from being buffered by Docker logs
ENV PYTHONUNBUFFERED 1
# Set the working directory in the container
WORKDIR /app

# Install system dependencies (if needed, uncomment the RUN line)
# psycopg2-binary *should* include pre-compiled binaries, but some systems or
# architectures might still require build tools and postgresql client dev headers.
# RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY ./swift_api /app/swift_api
COPY ./tests /app/tests

# Copy data file into the image
# Ensure the target directory exists
RUN mkdir -p /app/data
# Copy the specific Excel file (adjust filename if necessary)
COPY ./data/swift_codes.xlsx /app/data/swift_codes.xlsx

# Expose the port the app runs on
EXPOSE 8080

# Command to run the application using Uvicorn
# Use 0.0.0.0 to make it accessible from outside the container
CMD ["uvicorn", "swift_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
