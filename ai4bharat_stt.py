import os
import time
import requests

# ================= CONFIG =================
API_URL = os.getenv("AI4BHARAT_STT_URL", "http://74.225.216.132:8001/stt")
API_KEY = os.getenv("AI4BHARAT_API_KEY")

if not API_KEY:
    raise RuntimeError("AI4BHARAT_API_KEY environment variable not set")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}"
}

SUPPORTED_EXT = (".wav", ".mp3", ".flac", ".m4a", ".ogg")

MODEL_NAME = "ai4bharat-open-source-vm"


def transcribe(audio_path: str) -> dict:
    """
    Standardized AI4Bharat STT transcription via Azure VM.

    Returns:
        dict: {
            "provider": "AI4Bharat",
            "model": "<model_name>",
            "text": "<transcript>",
            "latency_ms": <float>
        }
    """

    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if not audio_path.lower().endswith(SUPPORTED_EXT):
        raise RuntimeError("Unsupported audio format")

    start_time = time.time()

    with open(audio_path, "rb") as f:
        files = {"file": f}
        response = requests.post(
            API_URL,
            headers=HEADERS,
            files=files,
            timeout=120
        )

    latency_ms = round((time.time() - start_time) * 1000, 2)

    if response.status_code != 200:
        raise RuntimeError(
            f"AI4Bharat STT failed: {response.status_code} - {response.text}"
        )

    data = response.json()

    transcript_text = (
        data.get("text")
        or data.get("transcription")
        or ""
    )

    return {
        "provider": "AI4Bharat",
        "model": MODEL_NAME,
        "text": transcript_text,
        "latency_ms": latency_ms
    }
