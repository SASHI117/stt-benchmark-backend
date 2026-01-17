import os
import tempfile
from typing import Optional
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
from google_stt import transcribe as google

# ================= FASTAPI APP =================
app = FastAPI(
    title="STT Benchmark Backend",
    description="Compare multiple STT providers using WER and latency",
    version="1.0"
)

# ================= STARTUP =================
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

# ================= AUTO-DETECT PROVIDERS =================
AUTO_PROVIDERS = [
    ("Azure", azure),
    ("ElevenLabs", elevenlabs),
    ("OpenAI", openai),
    ("Rev.ai", revai),
    ("Sarvam", sarvam),
    ("Soniox", soniox),
]

# ================= HEALTH =================
@app.get("/")
def health():
    return {"status": "Backend running"}

# ================= BENCHMARK =================
@app.post("/benchmark")
def benchmark(
    audio: UploadFile = File(...),
    reference_text: str = Form(...),
    language_code: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    if not reference_text.strip():
        raise HTTPException(status_code=400, detail="Reference text cannot be empty")

    if not audio.filename:
        raise HTTPException(status_code=400, detail="Audio file is required")

    allowed_extensions = (".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm")
    if not audio.filename.lower().endswith(allowed_extensions):
        raise HTTPException(status_code=400, detail="Unsupported audio format")

    if language_code is not None:
        language_code = language_code.strip() or None

    # ---------- CREATE RUN ----------
    run = BenchmarkRun(
        audio_filename=audio.filename,
        reference_text=reference_text
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    results = []

    # ---------- SAVE AUDIO ----------
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio.file.read())
        audio_path = tmp.name

    try:
        # ===== AUTO PROVIDERS =====
        for provider_name, provider_func in AUTO_PROVIDERS:
            try:
                provider_result = provider_func(audio_path)

                # 🔹 MULTI-MODEL PROVIDER (OpenAI)
                if isinstance(provider_result, list):
                    for r in provider_result:
                        wer_value = word_error_rate(reference_text, r["text"])

                        results.append({
                            "provider": r["provider"],
                            "model": r["model"],
                            "text": r["text"],
                            "wer": wer_value,
                            "latency_ms": r["latency_ms"],
                            "status": "success"
                        })

                        db.add(BenchmarkResult(
                            run_id=run.id,
                            provider=r["provider"],
                            model=r["model"],
                            transcript=r["text"],
                            wer=wer_value,
                            latency_ms=r["latency_ms"]
                        ))

                # 🔹 SINGLE-MODEL PROVIDER
                else:
                    wer_value = word_error_rate(reference_text, provider_result["text"])

                    results.append({
                        "provider": provider_name,
                        "model": None,
                        "text": provider_result["text"],
                        "wer": wer_value,
                        "latency_ms": provider_result["latency_ms"],
                        "status": "success"
                    })

                    db.add(BenchmarkResult(
                        run_id=run.id,
                        provider=provider_name,
                        model=None,
                        transcript=provider_result["text"],
                        wer=wer_value,
                        latency_ms=provider_result["latency_ms"]
                    ))

            except Exception as e:
                results.append({
                    "provider": provider_name,
                    "model": None,
                    "text": "",
                    "wer": None,
                    "latency_ms": None,
                    "status": "failed",
                    "error": str(e)
                })

        # ===== GOOGLE STT =====
        if language_code is None:
            results.append({
                "provider": "Google",
                "model": None,
                "text": "",
                "wer": None,
                "latency_ms": None,
                "status": "skipped",
                "error": "language_code is required for Google STT"
            })
        else:
            try:
                result = google(audio_path, language_code)
                wer_value = word_error_rate(reference_text, result["text"])

                results.append({
                    "provider": "Google",
                    "model": None,
                    "text": result["text"],
                    "wer": wer_value,
                    "latency_ms": result["latency_ms"],
                    "status": "success"
                })

                db.add(BenchmarkResult(
                    run_id=run.id,
                    provider="Google",
                    model=None,
                    transcript=result["text"],
                    wer=wer_value,
                    latency_ms=result["latency_ms"]
                ))

            except Exception as e:
                results.append({
                    "provider": "Google",
                    "model": None,
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
