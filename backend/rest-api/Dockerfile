# Use Python 3.11 slim base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install Poetry
RUN pip install poetry

# Disable Poetry's virtual environment creation
RUN poetry config virtualenvs.create false

# Copy Poetry configuration files (excluding README.md)
COPY pyproject.toml poetry.lock /app/

# Install dependencies with Poetry, without dev dependencies
RUN poetry install --only main --no-root

# Copy the rest of the backend rest-api code into /app
COPY . /app/

# Copy the frontend code to a subdirectory in /app
COPY ../../. /app/frontend/

# Expose the port for FastAPI
EXPOSE 8000

# Start FastAPI using Poetry
CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
