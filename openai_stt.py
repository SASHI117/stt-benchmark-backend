import os
import time
from openai import OpenAI


# OpenAI STT models you want to benchmark
OPENAI_STT_MODELS = [
    "gpt-4o-transcribe",
    "gpt-4o-mini-transcribe",
    "whisper-1"
]


def transcribe(audio_path: str) -> list[dict]:
    """
    Run OpenAI Speech-to-Text using multiple models.

    Returns:
        List of dicts:
        [
            {
                "provider": "OpenAI",
                "model": "<model_name>",
                "text": "<transcript>",
                "latency_ms": <float>
            },
            ...
        ]
    """

    # -------- API KEY --------
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set")

    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    client = OpenAI(api_key=api_key)

    results = []

    for model in OPENAI_STT_MODELS:
        start_time = time.time()

        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model=model,
                file=audio_file
            )

        latency_ms = round((time.time() - start_time) * 1000, 2)

        results.append({
            "provider": "OpenAI",
            "model": model,
            "text": transcription.text,
            "latency_ms": latency_ms
        })

    return results
