import io
import time

import pytest
from fastapi.testclient import TestClient

import main
from database import SessionLocal
from models import BenchmarkResult
from polling import ProviderTimeout, poll_until


def fake_single(audio_path):
    return {"provider": "Single", "model": "s-1", "text": "the cat sat", "latency_ms": 10.0}


def fake_multi(audio_path):
    return [
        {"provider": "Multi", "model": "good", "text": "the dog sat", "latency_ms": 5.0},
        {"provider": "Multi", "model": "broken", "text": "", "latency_ms": None,
         "error": "model not available"},
    ]


def fake_needs_lang(audio_path, language_code):
    return {"provider": "Lang", "model": language_code, "text": "the cat sat", "latency_ms": 1.0}


def fake_crash(audio_path):
    raise RuntimeError("API key missing")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "PROVIDERS", [
        main.Provider("Single", fake_single),
        main.Provider("Multi", fake_multi),
        main.Provider("Lang", fake_needs_lang, needs_language=True),
        main.Provider("Crash", fake_crash),
    ])
    with TestClient(main.app) as c:
        yield c


def post(client, filename="clip.wav", reference="The cat sat.", language=None):
    data = {"reference_text": reference}
    if language:
        data["language_code"] = language
    return client.post(
        "/benchmark",
        files={"audio": (filename, io.BytesIO(b"RIFF....WAVE"), "audio/wav")},
        data=data,
    )


def by_model(results):
    return {(r["provider"], r["model"]): r for r in results}


def test_health(client):
    assert client.get("/").json() == {"status": "Backend running"}


def test_benchmark_scores_and_statuses(client):
    resp = post(client, language="te-IN")
    assert resp.status_code == 200
    rows = by_model(resp.json()["results"])

    assert rows[("Single", "s-1")]["wer"] == 0.0
    assert rows[("Single", "s-1")]["status"] == "success"
    assert rows[("Multi", "good")]["wer"] == pytest.approx(1 / 3, abs=1e-4)
    # model-level error is reported as failed, not scored as an empty transcript
    assert rows[("Multi", "broken")]["status"] == "failed"
    assert rows[("Multi", "broken")]["wer"] is None
    assert rows[("Lang", "te-IN")]["status"] == "success"
    assert rows[("Crash", None)]["status"] == "failed"
    assert "API key missing" in rows[("Crash", None)]["error"]


def test_language_providers_skipped_without_language(client):
    rows = by_model(post(client).json()["results"])
    assert rows[("Lang", None)]["status"] == "skipped"


def test_only_successful_rows_are_persisted(client):
    run_id = post(client, language="hi-IN").json()["run_id"]
    with SessionLocal() as db:
        saved = db.query(BenchmarkResult).filter_by(run_id=run_id).all()
    assert sorted(r.model for r in saved) == ["good", "hi-IN", "s-1"]


@pytest.mark.parametrize("filename, reference, code", [
    ("clip.txt", "hello", 400),
    ("clip.wav", "   ", 400),
])
def test_rejects_bad_input(client, filename, reference, code):
    assert post(client, filename=filename, reference=reference).status_code == code


def test_upload_keeps_extension(client, monkeypatch):
    seen = {}

    def spy(audio_path):
        seen["path"] = audio_path
        return fake_single(audio_path)

    monkeypatch.setattr(main, "PROVIDERS", [main.Provider("Spy", spy)])
    post(client, filename="field_recording.MP3")
    assert seen["path"].endswith(".mp3")


def test_poll_until_times_out():
    with pytest.raises(ProviderTimeout):
        poll_until(lambda: "running", is_done=lambda s: s == "done",
                   timeout_s=0.05, interval_s=0.01)


def test_poll_until_surfaces_failure():
    with pytest.raises(RuntimeError, match="failed"):
        poll_until(lambda: "failed", is_done=lambda s: False,
                   is_failed=lambda s: s == "failed", interval_s=0)


def test_poll_until_returns_when_done():
    t0 = time.monotonic()
    states = iter(["queued", "running", "done"])
    assert poll_until(lambda: next(states), is_done=lambda s: s == "done",
                      interval_s=0) == "done"
    assert time.monotonic() - t0 < 1
