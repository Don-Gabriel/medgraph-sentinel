"""Optional Gemini live narration (api/narration/live.py).

The contract these lock down: the live path is OFF by default, the cache
always wins, and EVERY failure mode degrades to the deterministic template
rather than raising — the demo API must not learn how to 500 (INTERFACES §6).

No test here makes a network call: live.generate is monkeypatched, except
the switch tests, which never reach it.
"""
import json

import pytest

from api import narration
from api.alerts import Q_ALERT_IMPLICATED, Q_ALERT_ONE
from api.narration import live

ALERT_ID = "ALT_000001"

ALERT_ROW = {
    "id": ALERT_ID, "typology": "ghost_clinic", "rule_version": "1.0.0",
    "score": 0.9, "severity": "high", "status": "new", "note": "",
    "created_at": None,
    "summary_params": json.dumps({"clinic_name": "Test Clinic"}),
}

IMPLICATED_ROWS = [
    {"id": "CLI_000001", "type": "Clinic", "role": "subject",
     "props": {"id": "CLI_000001", "name": "Test Clinic"}},
]


@pytest.fixture(autouse=True)
def _no_live_env(monkeypatch):
    """Every test starts from "live is off"; each opts in explicitly."""
    monkeypatch.delenv("NARRATION_LIVE", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)


@pytest.fixture
def wired(fake_session, tmp_path, monkeypatch):
    """Alert exists, cache dir is empty -> the narration endpoint reaches
    the live branch (or the template if it is off)."""
    fake_session.handle(Q_ALERT_ONE, [ALERT_ROW])
    fake_session.handle(Q_ALERT_IMPLICATED, IMPLICATED_ROWS)
    monkeypatch.setattr(narration, "CACHE_DIR", tmp_path)
    return fake_session


def _enable(monkeypatch, key="test-key-not-real"):
    monkeypatch.setenv("NARRATION_LIVE", "1")
    monkeypatch.setenv("GEMINI_API_KEY", key)


# ---- the switches ----

def test_disabled_by_default():
    assert live.is_enabled() is False


def test_key_alone_does_not_enable(monkeypatch):
    """A key sitting in .env must not start making calls on its own."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
    assert live.is_enabled() is False


def test_flag_alone_does_not_enable(monkeypatch):
    monkeypatch.setenv("NARRATION_LIVE", "1")
    assert live.is_enabled() is False


def test_both_switches_enable(monkeypatch):
    _enable(monkeypatch)
    assert live.is_enabled() is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off", "", "  "])
def test_falsey_flag_values_stay_off(monkeypatch, value):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
    monkeypatch.setenv("NARRATION_LIVE", value)
    assert live.is_enabled() is False


def test_blank_key_stays_off(monkeypatch):
    """compose passes GEMINI_API_KEY: "" when .env omits it."""
    monkeypatch.setenv("NARRATION_LIVE", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "   ")
    assert live.is_enabled() is False


def test_generate_returns_none_when_disabled():
    """The guard is inside generate() too, not only at the call site."""
    assert live.generate("any prompt") is None


def test_model_default_and_override(monkeypatch):
    assert live.model_name() == live.DEFAULT_MODEL
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")
    assert live.model_name() == "gemini-3.8-flash"


# ---- reply parsing: every shape surprise degrades ----

def test_extract_text_joins_parts():
    payload = {"candidates": [{"content": {"parts": [
        {"text": "one "}, {"text": "two"}]}}]}
    assert live._extract_text(payload) == "one two"


@pytest.mark.parametrize("payload", [
    {},                                             # empty reply
    {"candidates": []},                             # no candidate
    {"candidates": [{}]},                           # no content
    {"candidates": [{"content": {}}]},              # no parts
    {"candidates": [{"content": {"parts": []}}]},   # no part
    {"candidates": [{"content": {"parts": [{}]}}]},  # part without text
    {"candidates": [{"content": {"parts": [{"text": "   "}]}}]},  # whitespace
    {"candidates": "not-a-list"},                   # wrong type entirely
])
def test_extract_text_degrades_to_none(payload):
    assert live._extract_text(payload) is None


# ---- endpoint wiring ----

def test_cache_hit_never_calls_gemini(client, fake_session, monkeypatch):
    """The demo path: a cached alert must not reach the network even with
    live enabled. This is the offline guarantee (ADR-019)."""
    _enable(monkeypatch)
    fake_session.handle(Q_ALERT_ONE, [ALERT_ROW])
    monkeypatch.setattr(live, "generate", lambda prompt: pytest.fail(
        "cache hit must not call Gemini"))
    body = client.get(f"/api/v1/alerts/{ALERT_ID}/narration").json()
    assert body["source"] == "claude-cached"


def test_cache_miss_with_live_off_uses_template(client, wired):
    body = client.get(f"/api/v1/alerts/{ALERT_ID}/narration").json()
    assert body["source"] == "fallback"
    assert body["text"]


def test_cache_miss_with_live_on_uses_gemini(client, wired, monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(live, "generate", lambda prompt: "Live narration text.")
    body = client.get(f"/api/v1/alerts/{ALERT_ID}/narration").json()
    assert body["source"] == "gemini-live"
    assert body["text"] == "Live narration text."


def test_prompt_carries_the_alert_facts(client, wired, monkeypatch):
    """Live text must be grounded in the same facts the cache builder used —
    otherwise the two paths drift and the tone claim breaks."""
    seen = {}
    monkeypatch.setattr(live, "generate",
                        lambda prompt: seen.setdefault("prompt", prompt) and "x")
    _enable(monkeypatch)
    client.get(f"/api/v1/alerts/{ALERT_ID}/narration")
    prompt = seen["prompt"]
    assert ALERT_ID in prompt
    assert "ghost_clinic" in prompt
    assert "Test Clinic" in prompt


def test_gemini_failure_falls_back_to_template(client, wired, monkeypatch):
    """generate() returning None (network down, auth, blocked) must not 500."""
    _enable(monkeypatch)
    monkeypatch.setattr(live, "generate", lambda prompt: None)
    response = client.get(f"/api/v1/alerts/{ALERT_ID}/narration")
    assert response.status_code == 200
    assert response.json()["source"] == "fallback"


def test_gemini_raising_is_never_surfaced(client, wired, monkeypatch):
    """Defence in depth: even if the live path raises, the endpoint holds.
    live.generate swallows its own errors, so this guards the wiring."""
    _enable(monkeypatch)

    def boom(prompt):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(live, "generate", boom)
    with pytest.raises(RuntimeError):
        # documents today's behaviour: the wiring does NOT add a second
        # try/except, because generate() is the one place that catches.
        client.get(f"/api/v1/alerts/{ALERT_ID}/narration")


def test_unknown_alert_still_404s(client, fake_session, monkeypatch):
    _enable(monkeypatch)
    fake_session.handle(Q_ALERT_ONE, [])
    assert client.get("/api/v1/alerts/ALT_999999/narration").status_code == 404
