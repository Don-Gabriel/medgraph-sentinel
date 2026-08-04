"""Live-narration tier tests (ADR-037): opt-in gating, live-first ordering,
fall-through to cache on any live failure, and the never-raise adapter
contract. The Gemini transport itself is always faked — no test touches
the network."""
import json
import urllib.request

import pytest

from api import narration
from api.alerts import Q_ALERT_IMPLICATED, Q_ALERT_ONE
from api.narration import live

ALERT = {"id": "ALT_000001", "typology": "ghost_clinic", "rule_version": "1.0",
         "score": 91.5, "severity": "high", "status": "new", "note": "",
         "created_at": "2026-07-30T12:47:37Z",
         "summary_params": json.dumps({
             "clinic_name": "Elysium Care Clinic", "claim_count": 132})}


@pytest.fixture
def api(client, fake_session):
    fake_session.handle(
        Q_ALERT_ONE, lambda p: [ALERT] if p["id"] == ALERT["id"] else [])
    fake_session.handle(Q_ALERT_IMPLICATED, lambda p: [
        {"id": "CLI_000217", "type": "Clinic", "role": "ghost_clinic",
         "props": {"id": "CLI_000217", "name": "Elysium Care Clinic"}}])
    return client


def _enable(monkeypatch):
    monkeypatch.setenv("NARRATION_LIVE", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")


# ---- gating ----

def test_disabled_by_default(api, tmp_path, monkeypatch):
    monkeypatch.delenv("NARRATION_LIVE", raising=False)
    monkeypatch.setattr(narration, "CACHE_DIR", tmp_path)
    called = []
    monkeypatch.setattr(live, "generate",
                        lambda prompt: called.append(prompt) or "MUST NOT APPEAR")
    body = api.get("/api/v1/alerts/ALT_000001/narration").json()
    assert body["source"] == "fallback" and called == []


def test_flag_without_key_stays_off(api, tmp_path, monkeypatch):
    monkeypatch.setenv("NARRATION_LIVE", "true")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(narration, "CACHE_DIR", tmp_path)
    called = []
    monkeypatch.setattr(live, "generate",
                        lambda prompt: called.append(prompt) or "MUST NOT APPEAR")
    assert api.get("/api/v1/alerts/ALT_000001/narration").json()["source"] == "fallback"
    assert called == []


# ---- live-first ordering and fall-through ----

def test_live_wins_over_cache_when_enabled(api, tmp_path, monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(narration, "CACHE_DIR", tmp_path)
    (tmp_path / "ALT_000001.json").write_text(json.dumps(
        {"alert_id": "ALT_000001", "text": "cached text"}), encoding="utf-8")
    monkeypatch.setattr(live, "generate", lambda prompt: "Fresh live text.")
    body = api.get("/api/v1/alerts/ALT_000001/narration").json()
    assert body == {"alert_id": "ALT_000001", "text": "Fresh live text.",
                    "source": "gemini-live"}


def test_live_failure_falls_back_to_cache(api, tmp_path, monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(narration, "CACHE_DIR", tmp_path)
    (tmp_path / "ALT_000001.json").write_text(json.dumps(
        {"alert_id": "ALT_000001", "text": "cached text"}), encoding="utf-8")
    monkeypatch.setattr(live, "generate", lambda prompt: None)
    body = api.get("/api/v1/alerts/ALT_000001/narration").json()
    assert body == {"alert_id": "ALT_000001", "text": "cached text",
                    "source": "claude-cached"}


def test_live_failure_without_cache_hits_template(api, tmp_path, monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(narration, "CACHE_DIR", tmp_path)  # empty dir
    monkeypatch.setattr(live, "generate", lambda prompt: None)
    assert api.get("/api/v1/alerts/ALT_000001/narration").json()["source"] == "fallback"


def test_live_prompt_carries_alert_facts(api, tmp_path, monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(narration, "CACHE_DIR", tmp_path)
    seen = {}
    monkeypatch.setattr(live, "generate",
                        lambda prompt: seen.setdefault("prompt", prompt) and None)
    api.get("/api/v1/alerts/ALT_000001/narration")
    prompt = seen["prompt"]
    # the canonical compose_prompt facts, not some ad-hoc string
    assert "ALT_000001" in prompt
    assert "Elysium Care Clinic" in prompt
    assert "clinic_name" in prompt
    assert "ghost_clinic" in prompt


# ---- adapter contract ----

def test_generate_never_raises_on_transport_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def boom(*args, **kwargs):
        raise OSError("no network")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    assert live.generate("prompt") is None


def test_generate_never_raises_on_malformed_response(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b'{"unexpected": "shape"}'

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: FakeResp())
    assert live.generate("prompt") is None


def test_enabled_parses_truthy_values(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    for value, expect in [("true", True), ("1", True), ("YES", True),
                          ("false", False), ("", False), ("0", False)]:
        monkeypatch.setenv("NARRATION_LIVE", value)
        assert live.enabled() is expect, value
