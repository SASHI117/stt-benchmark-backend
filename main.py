import os
import tempfile
from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# ================= ENV =================
load_dotenv()

# ================= DATABASE =================
from database import get_db, init_db
from models import BenchmarkRun, BenchmarkResult

# ================= METRICS =================
from metrics.wer import word_error_rate

# ================= STT PROVIDERS =================
from azure_stt import transcribe as azure
from elevenlabs_stt import transcribe as elevenlabs
from openai_stt import transcribe as openai
from revai_stt import transcribe as revai
from sarvam_stt import transcribe as sarvam
from soniox_stt import transcribe as soniox

# ================= FASTAPI APP =================
app = FastAPI(
    title="STT Benchmark Backend",
    description="Compare multiple STT providers using WER and latency",
    version="1.0"
)

# ================= STARTUP (CRITICAL FIX) =================
@app.on_event("startup")
def startup_event():
    init_db()

# ================= CORS =================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= PROVIDERS =================
PROVIDERS = [
    ("Azure", azure),
    ("ElevenLabs", elevenlabs),
    ("OpenAI", openai),
    ("Rev.ai", revai),
    ("Sarvam", sarvam),
    ("Soniox", soniox),
]

# ================= HEALTH CHECK =================
@app.get("/")
def health():
    return {"status": "Backend running"}

# ================= BENCHMARK ENDPOINT =================
@app.post("/benchmark")
def benchmark(
    audio: UploadFile = File(...),
    reference_text: str = Form(...),
    db: Session = Depends(get_db)
):
    if not reference_text.strip():
        raise HTTPException(status_code=400, detail="Reference text cannot be empty")

    if not audio.filename:
        raise HTTPException(status_code=400, detail="Audio file is required")

    allowed_extensions = (".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm")
    if not audio.filename.lower().endswith(allowed_extensions):
        raise HTTPException(status_code=400, detail="Unsupported audio format")

    # ---------- CREATE RUN ----------
    run = BenchmarkRun(
        audio_filename=audio.filename,
        reference_text=reference_text
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    results = []

    # ---------- SAVE AUDIO TEMP ----------
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio.file.read())
        audio_path = tmp.name

    try:
        for provider_name, provider_func in PROVIDERS:
            try:
                result = provider_func(audio_path)

                wer_percent = round(
                    word_error_rate(reference_text, result["text"]) * 100,
                    2
                )

                response = {
                    "provider": provider_name,
                    "text": result["text"],
                    "wer": wer_percent,
                    "latency_ms": result["latency_ms"],
                    "status": "success"
                }

                db_result = BenchmarkResult(
                    run_id=run.id,
                    provider=provider_name,
                    transcript=result["text"],
                    wer=wer_percent,
                    latency_ms=result["latency_ms"]
                )

                db.add(db_result)
                results.append(response)

            except Exception as e:
                results.append({
                    "provider": provider_name,
                    "text": "",
                    "wer": None,
                    "latency_ms": None,
                    "status": "failed",
                    "error": str(e)
                })

        db.commit()

    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)

    return {
        "run_id": run.id,
        "results": results
    }
