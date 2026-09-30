# STT Benchmark — Backend

[![CI](https://github.com/SASHI117/stt-benchmark-backend/actions/workflows/ci.yml/badge.svg)](https://github.com/SASHI117/stt-benchmark-backend/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB)
![FastAPI](https://img.shields.io/badge/FastAPI-REST-009688)

A FastAPI service that sends one audio clip to eight speech-to-text providers
(eleven models) and scores each transcript against a reference with **word
error rate** and **latency**. I built it during my internship at FarmVaidya.ai
to compare ASR engines on Indian-language farmer audio. The question it
answers is *which provider is accurate enough, fast enough, on our audio*,
not on a vendor's English benchmark.

The web UI lives in [stt-benchmark-frontend](https://github.com/SASHI117/stt-benchmark-frontend).
The self-hosted AI4Bharat model it calls is [ai4bharat_stt](https://github.com/SASHI117/ai4bharat_stt).

## Architecture

```mermaid
flowchart TB
    UI[Static web UI] -- "audio + reference + language" --> API["POST /benchmark (FastAPI)"]
    API --> POOL{{"ThreadPoolExecutor: one task per provider"}}
    POOL --> AZ[Azure Speech] & OA["OpenAI ×3"] & EL["ElevenLabs ×2"] & RV[Rev.ai]
    POOL --> SV[Sarvam] & SX[Soniox] & GG["Google *"] & AI["AI4Bharat *<br/>(self-hosted)"]
    AZ & OA & EL & RV & SV & SX & GG & AI --> WER["transcripts → normalize → WER"]
    WER --> DB[(PostgreSQL / SQLite)]
    WER -. "scores + latency" .-> UI
```

`*` needs an explicit `language_code`. The others detect the language themselves.

| Module | Responsibility |
|---|---|
| `main.py` | Request validation, the provider table, concurrent fan-out, persistence |
| `*_stt.py` | One adapter per provider. Each returns `{provider, model, text, latency_ms}` (or a list for multi-model providers) |
| `polling.py` | `poll_until()`: deadline-bounded polling for async job APIs (Rev.ai, Soniox) |
| `metrics/` | Unicode-aware text normalization and Levenshtein WER |
| `database.py`, `models.py` | SQLAlchemy engine, `benchmark_runs` / `benchmark_results` tables |

## How a request is scored

1. The upload is written to a temp file **with its original extension**, since
   several SDKs pick the decoder from it.
2. Every provider runs concurrently. Each adapter times only its own call, so
   the reported latency is per provider. The total request time is the
   slowest provider, not the sum of all of them.
3. Each transcript and the reference are normalized: NFC → casefold →
   drop nukta and map Devanagari chandrabindu to anusvara → remove Unicode
   punctuation/symbols/format characters → collapse whitespace.
4. WER = (substitutions + deletions + insertions) / reference words, computed
   by word-level Levenshtein distance. It can exceed 1.0 when a provider
   hallucinates extra words.
5. Successful rows are written to the database. Failures come back with
   `status: failed|skipped` and an `error` message instead of a fake score.

### Indic-aware normalization

Scoring Indian-language transcripts fairly takes more than lower-casing and stripping punctuation:

- **Vowel signs and viramas are kept.** Punctuation is removed by Unicode category (`P*`, `S*`,
  `Cf`), not with a `\w` regex, because `\w` doesn't match combining marks such as Devanagari and
  Telugu matras.
- **Accepted spelling variants count as the same word.** Nukta forms (फ़सल / फसल) and Devanagari
  chandrabindu vs anusvara (गेहूँ / गेहूं) are unified. Telugu's arasunna, a distinct sound, is kept.
- `tests/test_metrics.py` covers each of these cases.

## API

### `POST /benchmark`

| field | type | required |
|---|---|---|
| `audio` | file (`.wav .mp3 .m4a .flac .ogg .webm`) | yes |
| `reference_text` | string | yes |
| `language_code` | BCP-47, e.g. `te-IN` | no (Google and AI4Bharat are skipped without it) |

```bash
curl -X POST localhost:8000/benchmark \
  -F audio=@clip.wav -F reference_text="నమస్కారం రైతు గారు" -F language_code=te-IN
```

Response shape (values are illustrative):

```json
{
  "run_id": 42,
  "results": [
    {"provider": "OpenAI", "model": "gpt-4o-transcribe", "text": "…", "wer": 0.125, "latency_ms": 1840.2, "status": "success"},
    {"provider": "Google", "model": null, "text": "", "wer": null, "latency_ms": null, "status": "skipped",
     "error": "language_code is required for Google"}
  ]
}
```

`GET /` is a health check, and `GET /providers` lists the providers and whether each needs a language code.

## Running it

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env        # fill in whichever provider keys you have
uvicorn main:app --reload
```

Without `DATABASE_URL`, results go to `./stt_benchmark.db` (SQLite). A
provider without credentials fails on its own and doesn't take down the
service, because SDKs are imported inside each adapter.

With Docker:

```bash
docker build -t stt-benchmark-backend .
docker run --env-file .env -p 8000:8000 stt-benchmark-backend
```

## Testing

```bash
pytest -q          # 25 tests, no network or API keys needed
ruff check .
```

The API tests replace the provider table with fakes and check scoring,
the `success/failed/skipped` semantics, what gets persisted, input
validation, and polling timeouts. CI runs them on every push, then builds
the Docker image and checks that it boots.

To check real credentials, run the live smoke script. Providers without
keys show as `SKIPPED`, and secrets are never printed:

```bash
python scripts/smoke_providers.py clip.wav --reference "…" --language te-IN
```

## Design decisions

- **One adapter per provider, one output shape.** New providers are a new
  file plus a line in `PROVIDERS`. Multi-model providers return a list, and a
  failing model reports its own error without hiding its siblings.
- **Failures are reported, not scored.** A provider or model that errors comes back as
  `failed` with its message and isn't persisted, so an outage never shows up as a bad WER.
- **Bounded waits.** Every direct HTTP call has a timeout, and async job APIs
  go through `poll_until()` with a deadline and a failure predicate. Vendor
  SDK calls (OpenAI, ElevenLabs, Sarvam, Azure) rely on the SDKs' own timeouts.
- **Full-length transcription everywhere.** Azure runs in continuous-recognition mode, so long
  clips are transcribed end to end like every other provider.

## Usage tips

- Benchmark over a set of clips per language, not a single upload, and compare the averages.
- Latency is measured end to end from this server, including network and upload time, which is
  what an application built on the provider actually experiences.
- Google STT v1's synchronous endpoint expects LINEAR16 WAV, so send WAV when Google is in the comparison.
- Run the API behind a gateway, or restrict `CORS_ORIGINS`, when deploying it publicly.

## Roadmap

- Numeral normalization ("20" vs "twenty") and transliteration-aware scoring.
- Batch benchmarking over a folder of clips with aggregate WER and latency percentiles.
- API authentication and per-user benchmark history.
