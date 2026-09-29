import os
import re
import time

import requests

from polling import HTTP_TIMEOUT_S, poll_until

LANG_ID_URL = "https://api.rev.ai/languageid/v1/jobs"


def clean_revai_text(text: str) -> str:
    """
    Remove speaker labels, timestamps, and extra whitespace
    from Rev.ai transcripts.
    """
    text = re.sub(r"Speaker\s+\d+", "", text)
    text = re.sub(r"\b\d{2}:\d{2}:\d{2}(\.\d+)?\b", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def transcribe(audio_path: str) -> dict:
    """
    Standardized Rev.ai STT transcription with language detection.
    """
    from rev_ai import JobStatus, apiclient

    token = os.getenv("REVAI_API_KEY")
    if not token:
        raise RuntimeError("REVAI_API_KEY environment variable not set")

    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    client = apiclient.RevAiAPIClient(token)
    headers = {"Authorization": f"Bearer {token}"}
    start_time = time.time()

    # ================= LANGUAGE IDENTIFICATION =================
    with open(audio_path, "rb") as f:
        response = requests.post(
            LANG_ID_URL, headers=headers, files={"media": f}, timeout=HTTP_TIMEOUT_S
        )
    response.raise_for_status()
    lang_job_id = response.json()["id"]

    poll_until(
        lambda: requests.get(
            f"{LANG_ID_URL}/{lang_job_id}", headers=headers, timeout=HTTP_TIMEOUT_S
        ).json(),
        is_done=lambda s: s["status"] == "completed",
        is_failed=lambda s: s["status"] == "failed",
        what="Rev.ai language identification",
    )

    result = requests.get(
        f"{LANG_ID_URL}/{lang_job_id}/result",
        headers={**headers, "Accept": "application/vnd.rev.languageid.v1.0+json"},
        timeout=HTTP_TIMEOUT_S,
    ).json()
    detected_language = result["top_language"]

    # ================= TRANSCRIPTION =================
    job = client.submit_job_local_file(audio_path, language=detected_language)

    poll_until(
        lambda: client.get_job_details(job.id),
        is_done=lambda d: d.status == JobStatus.TRANSCRIBED,
        is_failed=lambda d: d.status == JobStatus.FAILED,
        what="Rev.ai transcription",
    )

    transcript_text = clean_revai_text(client.get_transcript_text(job.id))
    latency_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "provider": "Rev.ai",
        "model": "machine",
        "text": transcript_text,
        "latency_ms": latency_ms,
    }
