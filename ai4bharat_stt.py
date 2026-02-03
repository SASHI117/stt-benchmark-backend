import os
import time
import requests


def transcribe(audio_path: str, language_code: str) -> dict:
    """
    Standardized AI4Bharat STT transcription.
    Language code REQUIRED (like Google).
    """

    api_url = os.getenv("AI4BHARAT_STT_URL")
    api_key = os.getenv("AI4BHARAT_API_KEY")

    if not api_url or not api_key:
        raise RuntimeError("AI4BHARAT_STT_URL or AI4BHARAT_API_KEY not set")

    if not language_code:
        raise RuntimeError("language_code is required for AI4Bharat")

    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # -------- Convert te-IN -> te --------
    lang = language_code.split("-")[0]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-Language": lang
    }

    with open(audio_path, "rb") as f:
        files = {"file": f}

        start_time = time.time()

        response = requests.post(
            api_url,
            headers=headers,
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
        "model": "ai4bharat-asr",
        "text": transcript_text,
        "latency_ms": latency_ms
    }
