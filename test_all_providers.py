import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

from azure_stt import transcribe as azure
from elevenlabs_stt import transcribe as elevenlabs
from openai_stt import transcribe as openai
from revai_stt import transcribe as revai
from sarvam_stt import transcribe as sarvam
from soniox_stt import transcribe as soniox


AUDIO_FILE = "test_audio/sample.wav"


def test_provider(name, func):
    print(f"\n==============================")
    print(f"Testing: {name}")
    print(f"==============================")
    try:
        result = func(AUDIO_FILE)
        print("✅ SUCCESS")
        print(result)
    except Exception as e:
        print("❌ FAILED")
        print(e)


if __name__ == "__main__":
    test_provider("Azure", azure)
    test_provider("ElevenLabs", elevenlabs)
    test_provider("OpenAI", openai)
    test_provider("Rev.ai", revai)
    test_provider("Sarvam", sarvam)
    test_provider("Soniox", soniox)
