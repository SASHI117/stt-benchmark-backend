import logging
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

logger = logging.getLogger(__name__)

# Railway-managed PostgreSQL in production; SQLite for local development.
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./stt_benchmark.db"

# Some hosts still hand out the pre-SQLAlchemy-1.4 "postgres://" scheme.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

_is_sqlite = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    """Create tables if they do not exist. Safe to run multiple times."""
    import models  # noqa: F401  (registers tables on Base.metadata)

    Base.metadata.create_all(bind=engine)
    # Never log the raw URL: it carries the database password.
    logger.info("Database ready: %s", make_url(DATABASE_URL).render_as_string(hide_password=True))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
