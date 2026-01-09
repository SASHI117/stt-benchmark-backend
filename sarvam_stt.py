import os
import time
import json
from pathlib import Path
from sarvamai import SarvamAI
import tempfile

MODEL = "saarika:v2.5"


def transcribe(audio_path: str) -> dict:
    """
    Standardized Sarvam STT transcription function
    (correct parsing based on actual SDK output)
    """

    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        raise RuntimeError("SARVAM_API_KEY environment variable not set")

    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    client = SarvamAI(api_subscription_key=api_key)

    start_time = time.time()

    job = client.speech_to_text_job.create_job(
        model=MODEL,
        language_code="unknown",
        with_diarization=True,
        with_timestamps=True,
        num_speakers=2
    )

    job.upload_files(file_paths=[str(audio_path)], timeout=120)
    job.start()
    job.wait_until_complete(poll_interval=5, timeout=600)

    latency_ms = round((time.time() - start_time) * 1000, 2)

    transcript_text = ""

    # ✅ CORRECT OUTPUT HANDLING
    with tempfile.TemporaryDirectory() as tmpdir:
        job.download_outputs(output_dir=tmpdir)

        for file in Path(tmpdir).glob("*.json"):
            data = json.loads(file.read_text(encoding="utf-8"))
            if "transcript" in data:
                transcript_text = data["transcript"].strip()
                break

    return {
        "provider": "Sarvam",
        "text": transcript_text,
        "latency_ms": latency_ms
    }
