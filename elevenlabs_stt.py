import os
import time

# ElevenLabs STT models
ELEVENLABS_STT_MODELS = [
    "scribe_v1",
    "scribe_v2"
]

def transcribe(audio_path: str) -> list[dict]:
    """
    Run ElevenLabs Speech-to-Text using multiple models.

    Returns:
        [
            {
                "provider": "ElevenLabs",
                "model": "<model_name>",
                "text": "<transcript>",
                "latency_ms": <float>
            },
            ...
        ]
    """

    from elevenlabs.client import ElevenLabs

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY environment variable not set")

    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    client = ElevenLabs(api_key=api_key)

    results = []

    for model_id in ELEVENLABS_STT_MODELS:
        try:
            start_time = time.time()

            with open(audio_path, "rb") as audio_file:
                response = client.speech_to_text.convert(
                    file=audio_file,
                    model_id=model_id
                )

            latency_ms = round((time.time() - start_time) * 1000, 2)

            results.append({
                "provider": "ElevenLabs",
                "model": model_id,
                "text": response.text,
                "latency_ms": latency_ms
            })

        except Exception as e:
            # One model failing should not hide the other model's result
            results.append({
                "provider": "ElevenLabs",
                "model": model_id,
                "text": "",
                "latency_ms": None,
                "error": str(e)
            })

    return results
