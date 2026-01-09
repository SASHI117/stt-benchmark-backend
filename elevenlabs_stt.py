import os
import time
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs


# Load environment variables from .env (ElevenLabs requirement)
load_dotenv(dotenv_path=".env", override=True)


def transcribe(audio_path: str) -> dict:
    """
    Standardized ElevenLabs STT transcription function.

    Args:
        audio_path (str): Path to audio file

    Returns:
        dict: {
            "provider": "ElevenLabs",
            "text": "<transcript>",
            "latency_ms": <float>
        }
    """

    # -------- API KEY (ENV VARIABLE) --------
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY environment variable not set")

    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    client = ElevenLabs(api_key=api_key)

    start_time = time.time()

    with open(audio_path, "rb") as audio_file:
        response = client.speech_to_text.convert(
            file=audio_file,
            model_id="scribe_v1"
        )

    latency_ms = round((time.time() - start_time) * 1000, 2)

    transcript_text = response.text

    return {
        "provider": "ElevenLabs",
        "text": transcript_text,
        "latency_ms": latency_ms
    }
