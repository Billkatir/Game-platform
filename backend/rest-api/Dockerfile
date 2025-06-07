FROM python:3.11-slim

WORKDIR /app

RUN pip install poetry
RUN poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock /app/

RUN poetry install --only main --no-root

RUN pip install websockets wsproto

COPY . /app/

COPY ../../. /app/frontend/

EXPOSE 8000

CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]