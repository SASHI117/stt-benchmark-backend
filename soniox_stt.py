import os
import time
import requests

SONIOX_API = "https://api.soniox.com"


def transcribe(audio_path: str) -> dict:
    """
    Standardized Soniox STT transcription function.

    Args:
        audio_path (str): Path to audio file

    Returns:
        dict: {
            "provider": "Soniox",
            "text": "<transcript>",
            "latency_ms": <float>
        }
    """

    # -------- API KEY (ENV VARIABLE ONLY) --------
    api_key = os.getenv("SONIOX_API_KEY")
    if not api_key:
        raise RuntimeError("SONIOX_API_KEY environment variable not set")

    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    start_time = time.time()

    # ================= STEP 1: Upload Audio =================
    with open(audio_path, "rb") as f:
        res = requests.post(
            f"{SONIOX_API}/v1/files",
            headers=headers,
            files={"file": f}
        )
    res.raise_for_status()
    file_id = res.json()["id"]

    # ================= STEP 2: Create Transcription =================
    payload = {
        "model": "stt-async-v3",
        "file_id": file_id,
        "enable_language_identification": True
    }

    res = requests.post(
        f"{SONIOX_API}/v1/transcriptions",
        headers=headers,
        json=payload
    )
    res.raise_for_status()
    transcription_id = res.json()["id"]

    # ================= STEP 3: Wait for Result =================
    while True:
        res = requests.get(
            f"{SONIOX_API}/v1/transcriptions/{transcription_id}",
            headers=headers
        )
        res.raise_for_status()
        data = res.json()

        if data["status"] == "completed":
            break
        elif data["status"] == "error":
            raise RuntimeError("Soniox transcription failed")

        time.sleep(1)

    # ================= STEP 4: Get Transcript =================
    res = requests.get(
        f"{SONIOX_API}/v1/transcriptions/{transcription_id}/transcript",
        headers=headers
    )
    res.raise_for_status()
    transcript = res.json()

    transcript_text = "".join(token["text"] for token in transcript["tokens"])

    latency_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "provider": "Soniox",
        "text": transcript_text,
        "latency_ms": latency_ms
    }
