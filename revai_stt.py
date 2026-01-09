import os
import time
import requests
from rev_ai import apiclient


def transcribe(audio_path: str) -> dict:
    """
    Standardized Rev.ai STT transcription with language detection.

    Args:
        audio_path (str): Path to audio file

    Returns:
        dict: {
            "provider": "Rev.ai",
            "text": "<transcript>",
            "latency_ms": <float>
        }
    """

    # -------- API KEY (ENV VARIABLE ONLY) --------
    token = os.getenv("REVAI_API_KEY")
    if not token:
        raise RuntimeError("REVAI_API_KEY environment variable not set")

    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    client = apiclient.RevAiAPIClient(token)

    start_time = time.time()

    # ================= LANGUAGE IDENTIFICATION =================
    LANG_ID_URL = "https://api.rev.ai/languageid/v1/jobs"
    headers = {"Authorization": f"Bearer {token}"}

    with open(audio_path, "rb") as f:
        response = requests.post(
            LANG_ID_URL,
            headers=headers,
            files={"media": f}
        )

    response.raise_for_status()
    lang_job_id = response.json()["id"]

    while True:
        status = requests.get(
            f"https://api.rev.ai/languageid/v1/jobs/{lang_job_id}",
            headers=headers
        ).json()

        if status["status"] == "completed":
            break
        time.sleep(1)

    result = requests.get(
        f"https://api.rev.ai/languageid/v1/jobs/{lang_job_id}/result",
        headers={
            **headers,
            "Accept": "application/vnd.rev.languageid.v1.0+json"
        }
    ).json()

    detected_language = result["top_language"]

    # ================= TRANSCRIPTION =================
    job = client.submit_job_local_file(
        audio_path,
        language=detected_language
    )

    while True:
        details = client.get_job_details(job.id)
        if details.status == "transcribed":
            break
        time.sleep(1)

    transcript_text = client.get_transcript_text(job.id)

    latency_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "provider": "Rev.ai",
        "text": transcript_text,
        "latency_ms": latency_ms
    }
