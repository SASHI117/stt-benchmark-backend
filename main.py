import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Callable, NamedTuple, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

load_dotenv()

from ai4bharat_stt import transcribe as ai4bharat  # noqa: E402
from azure_stt import transcribe as azure  # noqa: E402
from database import get_db, init_db  # noqa: E402
from elevenlabs_stt import transcribe as elevenlabs  # noqa: E402
from google_stt import transcribe as google  # noqa: E402
from metrics.wer import word_error_rate  # noqa: E402
from models import BenchmarkResult, BenchmarkRun  # noqa: E402
from openai_stt import transcribe as openai  # noqa: E402
from revai_stt import transcribe as revai  # noqa: E402
from sarvam_stt import transcribe as sarvam  # noqa: E402
from soniox_stt import transcribe as soniox  # noqa: E402

logging.basicConfig(level=logging.INFO)

ALLOWED_EXTENSIONS = (".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm")


class Provider(NamedTuple):
    name: str
    transcribe: Callable
    needs_language: bool = False


# Providers that detect the language themselves run on every request; the
# ones that need an explicit BCP-47 code are skipped when none is given.
PROVIDERS = [
    Provider("Azure", azure),
    Provider("ElevenLabs", elevenlabs),
    Provider("OpenAI", openai),
    Provider("Rev.ai", revai),
    Provider("Sarvam", sarvam),
    Provider("Soniox", soniox),
    Provider("Google", google, needs_language=True),
    Provider("AI4Bharat", ai4bharat, needs_language=True),
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="STT Benchmark Backend",
    description="Compare multiple STT providers using WER and latency",
    version="1.1",
    lifespan=lifespan,
)

# Browsers reject credentialed requests to a wildcard origin, so credentials
# are only enabled when explicit origins are configured.
_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _failed(provider: str, model: Optional[str], error: str, status: str = "failed") -> dict:
    return {
        "provider": provider,
        "model": model,
        "text": "",
        "wer": None,
        "latency_ms": None,
        "status": status,
        "error": error,
    }


def run_provider(provider: Provider, audio_path: str, language_code: Optional[str],
                 reference_text: str) -> list[dict]:
    """Run one provider and return one scored row per model it evaluated."""
    if provider.needs_language and not language_code:
        return [_failed(provider.name, None,
                        f"language_code is required for {provider.name}", status="skipped")]

    try:
        args = (audio_path, language_code) if provider.needs_language else (audio_path,)
        output = provider.transcribe(*args)
    except Exception as e:  # provider-level failure (auth, network, SDK)
        return [_failed(provider.name, None, str(e))]

    rows = []
    for r in output if isinstance(output, list) else [output]:
        name = r.get("provider", provider.name)
        if r.get("error"):
            # A model-level failure must not be scored as an empty transcript.
            rows.append(_failed(name, r.get("model"), r["error"]))
            continue
        rows.append({
            "provider": name,
            "model": r.get("model"),
            "text": r["text"],
            "wer": word_error_rate(reference_text, r["text"]),
            "latency_ms": r["latency_ms"],
            "status": "success",
        })
    return rows


@app.get("/")
def health():
    return {"status": "Backend running"}


@app.get("/providers")
def list_providers():
    return [{"name": p.name, "needs_language": p.needs_language} for p in PROVIDERS]


@app.post("/benchmark")
def benchmark(
    audio: UploadFile = File(...),
    reference_text: str = Form(...),
    language_code: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    if not reference_text.strip():
        raise HTTPException(status_code=400, detail="Reference text cannot be empty")

    if not audio.filename:
        raise HTTPException(status_code=400, detail="Audio file is required")

    suffix = os.path.splitext(audio.filename)[1].lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported audio format")

    language_code = (language_code or "").strip() or None

    # Keep the real extension: several SDKs pick the decoder from it.
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio.file.read())
        audio_path = tmp.name

    try:
        # Providers are remote APIs, so run them concurrently; each one times
        # its own call, so per-provider latency is unaffected. Total request
        # time becomes the slowest provider rather than the sum of all.
        with ThreadPoolExecutor(max_workers=len(PROVIDERS)) as pool:
            futures = [
                pool.submit(run_provider, p, audio_path, language_code, reference_text)
                for p in PROVIDERS
            ]
            results = [row for f in futures for row in f.result()]
    finally:
        os.remove(audio_path)

    # The SQLAlchemy session is not thread-safe: persist on this thread only.
    run = BenchmarkRun(
        audio_filename=audio.filename,
        reference_text=reference_text,
        language_code=language_code,
    )
    db.add(run)
    db.flush()
    for r in results:
        if r["status"] == "success":
            db.add(BenchmarkResult(
                run_id=run.id,
                provider=r["provider"],
                model=r["model"],
                transcript=r["text"],
                wer=r["wer"],
                latency_ms=r["latency_ms"],
            ))
    db.commit()

    return {"run_id": run.id, "results": results}
