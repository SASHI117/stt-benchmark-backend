import base64
import requests
import time
import os


def transcribe(audio_path: str, language_code: str) -> dict:
    """
    Standardized Google Speech-to-Text transcription.
    Language code is REQUIRED (Google does not auto-detect).
    """

    # -------- API KEY (ENV VARIABLE ONLY) --------
    api_key = os.getenv("GOOGLE_STT_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_STT_API_KEY environment variable not set")

    if not language_code:
        raise RuntimeError("language_code is required for Google STT")

    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    url = f"https://speech.googleapis.com/v1/speech:recognize?key={api_key}"

    # -------- READ & BASE64 ENCODE AUDIO --------
    with open(audio_path, "rb") as audio_file:
        audio_bytes = audio_file.read()
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

    # -------- REQUEST PAYLOAD --------
    payload = {
        "config": {
            "encoding": "LINEAR16",
            "languageCode": language_code
        },
        "audio": {
            "content": audio_base64
        }
    }

    # -------- SEND REQUEST --------
    start_time = time.time()
    response = requests.post(url, json=payload)
    latency_ms = round((time.time() - start_time) * 1000, 2)

    # -------- PARSE RESPONSE --------
    transcript_text = ""

    if response.status_code == 200:
        data = response.json()
        if "results" in data and data["results"]:
            transcript_text = (
                data["results"][0]["alternatives"][0]["transcript"]
            )
    else:
        raise RuntimeError(
            f"Google STT failed: {response.status_code} - {response.text}"
        )

    return {
        "provider": "Google",
        "model": "google-stt-standard",  # ✅ ADDED
        "text": transcript_text,
        "latency_ms": latency_ms
    }
