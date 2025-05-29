from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from contextlib import contextmanager
import time

# PostgreSQL database URL
POSTGRESQL_DATABASE_URL = "postgresql://admin:admin@postgres:5432/greenhouse"

# Retry settings
MAX_RETRIES = 20
RETRY_DELAY = 5  # seconds

# Function to create SQLAlchemy engine with retry logic
def create_postgresql_engine(url, max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY):
    retries = 0
    while retries < max_retries:
        try:
            engine = create_engine(url)
            # Test the connection
            with engine.connect() as connection:
                print("Connected to PostgreSQL successfully.")
            return engine
        except OperationalError as e:
            print(f"Connection to PostgreSQL failed: {e}. Retrying in {retry_delay} seconds... ({max_retries - retries} retries left)")
            time.sleep(retry_delay)
            retries += 1
    raise Exception("Database connection failed after multiple retries")

# Create SQLAlchemy engine for PostgreSQL with retry logic
postgresql_engine = create_postgresql_engine(POSTGRESQL_DATABASE_URL)

@contextmanager
def get_postgresql_session() -> Session:
    SessionLocal = sessionmaker(bind=postgresql_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
