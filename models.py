from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id = Column(Integer, primary_key=True, index=True)
    audio_filename = Column(String, nullable=False)
    reference_text = Column(String, nullable=False)

    # ✅ NEW (optional, for Google / future AI4Bharat)
    language_code = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("benchmark_runs.id"), nullable=False)

    provider = Column(String, nullable=False)
    transcript = Column(String, nullable=False)
    wer = Column(Float, nullable=False)
    latency_ms = Column(Float, nullable=False)
