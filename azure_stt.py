import os
import threading
import time

from polling import JOB_TIMEOUT_S

CANDIDATE_LANGUAGES = ["en-US", "hi-IN", "te-IN", "ta-IN"]


def transcribe(audio_path: str) -> dict:
    """
    Standardized Azure Speech-to-Text transcription with auto language detection.

    Uses continuous recognition: recognize_once() stops at the first pause
    (at most ~15 s of speech), which truncated longer clips and inflated
    Azure's WER relative to providers that transcribe the whole file.
    """
    import azure.cognitiveservices.speech as speechsdk

    # -------- API KEYS (ENV VARIABLES ONLY) --------
    speech_key = os.getenv("SPEECH_KEY")
    endpoint = os.getenv("ENDPOINT")

    if not speech_key or not endpoint:
        raise RuntimeError("SPEECH_KEY or ENDPOINT environment variable not set")

    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, endpoint=endpoint)
    auto_detect_config = speechsdk.AutoDetectSourceLanguageConfig(
        languages=CANDIDATE_LANGUAGES
    )
    audio_config = speechsdk.audio.AudioConfig(filename=audio_path)

    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_config,
        auto_detect_source_language_config=auto_detect_config,
    )

    segments: list[str] = []
    errors: list[str] = []
    done = threading.Event()

    def on_recognized(evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            segments.append(evt.result.text)

    def on_canceled(evt):
        # EndOfStream is the normal end of a file; anything else is a failure.
        if evt.cancellation_details.reason == speechsdk.CancellationReason.Error:
            errors.append(evt.cancellation_details.error_details)
        done.set()

    recognizer.recognized.connect(on_recognized)
    recognizer.canceled.connect(on_canceled)
    recognizer.session_stopped.connect(lambda _evt: done.set())

    start_time = time.time()
    recognizer.start_continuous_recognition()
    finished = done.wait(timeout=JOB_TIMEOUT_S)
    recognizer.stop_continuous_recognition()
    latency_ms = round((time.time() - start_time) * 1000, 2)

    if errors:
        raise RuntimeError(f"Azure STT canceled: {errors[0]}")
    if not finished:
        raise RuntimeError(f"Azure STT did not finish within {JOB_TIMEOUT_S}s")

    return {
        "provider": "Azure",
        "model": "azure-stt-auto-lang",
        "text": " ".join(segments).strip(),
        "latency_ms": latency_ms,
    }
