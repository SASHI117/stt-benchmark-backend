"""Live smoke test: run every configured STT provider on one audio file.

Providers whose credentials are not set are reported as SKIPPED instead of
failing, so this is safe to run with any subset of keys. Secrets are never
printed.

    python scripts/smoke_providers.py path/to/clip.wav --reference "..." --language te-IN
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

import main  # noqa: E402

REQUIRED_ENV = {
    "Azure": ["SPEECH_KEY", "ENDPOINT"],
    "ElevenLabs": ["ELEVENLABS_API_KEY"],
    "OpenAI": ["OPENAI_API_KEY"],
    "Rev.ai": ["REVAI_API_KEY"],
    "Sarvam": ["SARVAM_API_KEY"],
    "Soniox": ["SONIOX_API_KEY"],
    "Google": ["GOOGLE_STT_API_KEY"],
    "AI4Bharat": ["AI4BHARAT_STT_URL", "AI4BHARAT_API_KEY"],
}


def main_cli() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--reference", required=True)
    ap.add_argument("--language", default=None, help="BCP-47 code, e.g. te-IN")
    args = ap.parse_args()

    print(f"{'provider':<12} {'model':<24} {'status':<8} {'WER':>6} {'latency':>10}")
    for provider in main.PROVIDERS:
        missing = [k for k in REQUIRED_ENV.get(provider.name, []) if not os.getenv(k)]
        if missing:
            print(f"{provider.name:<12} {'-':<24} {'SKIPPED':<8} (unset: {', '.join(missing)})")
            continue
        for r in main.run_provider(provider, args.audio, args.language, args.reference):
            wer = f"{r['wer']:.3f}" if r["wer"] is not None else "-"
            lat = f"{r['latency_ms']:.0f} ms" if r["latency_ms"] is not None else "-"
            print(f"{r['provider']:<12} {str(r['model']):<24} {r['status']:<8} {wer:>6} {lat:>10}")
            if r.get("error"):
                print(f"{'':<12} error: {r['error'][:160]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
