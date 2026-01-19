import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# 🔹 Fallback to SQLite for local/dev only
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./stt_benchmark.db"

# 🔥 FIX: Railway/Postgres-safe engine configuration
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # prevents SSL EOF errors
    pool_recycle=300     # avoids stale connections
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def init_db():
    """
    Create tables if they do not exist.
    Safe to run multiple times.
    """
    from models import BenchmarkRun, BenchmarkResult  # ensure models are registered
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
