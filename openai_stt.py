import os
import time
from openai import OpenAI


def transcribe(audio_path: str) -> dict:
    """
    Standardized OpenAI STT transcription function.

    Args:
        audio_path (str): Path to audio file

    Returns:
        dict: {
            "provider": "OpenAI",
            "text": "<transcript>",
            "latency_ms": <float>
        }
    """

    # -------- API KEY (ENV VARIABLE ONLY) --------
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set")

    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    client = OpenAI(api_key=api_key)

    start_time = time.time()

    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=audio_file
        )

    latency_ms = round((time.time() - start_time) * 1000, 2)

    transcript_text = transcription.text

    return {
        "provider": "OpenAI",
        "text": transcript_text,
        "latency_ms": latency_ms
    }
