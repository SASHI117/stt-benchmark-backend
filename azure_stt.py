import os
import time
import azure.cognitiveservices.speech as speechsdk


def transcribe(audio_path: str) -> dict:
    """
    Standardized Azure Speech-to-Text transcription with auto language detection.

    Args:
        audio_path (str): Path to audio file

    Returns:
        dict: {
            "provider": "Azure",
            "text": "<transcript>",
            "latency_ms": <float>
        }
    """

    # -------- API KEYS (ENV VARIABLES ONLY) --------
    speech_key = os.getenv("SPEECH_KEY")
    endpoint = os.getenv("ENDPOINT")

    if not speech_key or not endpoint:
        raise RuntimeError("SPEECH_KEY or ENDPOINT environment variable not set")

    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    speech_config = speechsdk.SpeechConfig(
        subscription=speech_key,
        endpoint=endpoint
    )

    # ================= AUTO LANGUAGE DETECTION =================
    candidate_languages = [
        "en-US",
        "hi-IN",
        "te-IN",
        "ta-IN"
    ]

    # Compatible with OLD + NEW SDKs
    try:
        auto_detect_config = speechsdk.AutoDetectSourceLanguageConfig.from_languages(
            candidate_languages
        )
    except AttributeError:
        auto_detect_config = speechsdk.AutoDetectSourceLanguageConfig(
            languages=candidate_languages
        )

    audio_config = speechsdk.audio.AudioConfig(filename=audio_path)

    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_config,
        auto_detect_source_language_config=auto_detect_config
    )

    start_time = time.time()
    result = recognizer.recognize_once_async().get()
    latency_ms = round((time.time() - start_time) * 1000, 2)

    transcript_text = ""

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        transcript_text = result.text

    elif result.reason == speechsdk.ResultReason.NoMatch:
        transcript_text = ""

    elif result.reason == speechsdk.ResultReason.Canceled:
        raise RuntimeError(
            f"Azure STT canceled: {result.cancellation_details.reason} - "
            f"{result.cancellation_details.error_details}"
        )

    return {
        "provider": "Azure",
        "text": transcript_text,
        "latency_ms": latency_ms
    }
