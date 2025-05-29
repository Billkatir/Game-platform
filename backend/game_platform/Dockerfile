# Use Python 3.11 slim base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install Poetry
RUN pip install poetry

# Configure Poetry: Important to ensure it does not create a virtual environment
RUN poetry config virtualenvs.create false

# Copy Poetry configuration files (excluding README.md)
COPY pyproject.toml poetry.lock /app/

# Install dependencies with Poetry
RUN poetry install --only main --no-root
# Copy the backend code
COPY . /app/

# Start FastAPI or your main Python script
CMD ["python", "-u", "main.py"]
