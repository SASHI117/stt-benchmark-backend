import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# 🔹 Fallback to SQLite for local/dev only
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./stt_benchmark.db"

# 🧪 DEBUG: Print DB URL (safe – password masked by Railway logs)
print("🔍 DATABASE_URL IN USE:", DATABASE_URL)

# 🔥 Railway/Postgres-safe engine configuration
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
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
    from models import BenchmarkRun, BenchmarkResult
    Base.metadata.create_all(bind=engine)

    # 🧪 DEBUG: Confirm connected DB + schema + table columns
    with engine.connect() as conn:
        db_name = conn.execute(text("SELECT current_database();")).scalar()
        schema = conn.execute(text("SELECT current_schema();")).scalar()

        print("🧪 Connected database:", db_name)
        print("🧪 Active schema:", schema)

        cols = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'benchmark_results';
        """)).fetchall()

        print("🧪 benchmark_results columns:", [c[0] for c in cols])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
