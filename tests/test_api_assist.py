"""Assist endpoint tests (ADR-038): report live/fallback tiers, chat
gating and validation, context-boundedness of the prompts. The live
transport is always faked."""
import json

import pytest

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


# ---- report ----

def test_report_fallback_is_complete_offline(api, monkeypatch):
    monkeypatch.delenv("NARRATION_LIVE", raising=False)
    body = api.get("/api/v1/alerts/ALT_000001/report").json()
    assert body["source"] == "fallback"
    for section in ("CASE SUMMARY", "KEY EVIDENCE", "ASSESSMENT",
                    "RECOMMENDED ACTIONS", "LIMITATIONS"):
        assert section in body["report"], section
    assert "Elysium Care Clinic" in body["report"]


def test_report_live_when_enabled(api, monkeypatch):
    _enable(monkeypatch)
    seen = {}
    monkeypatch.setattr(live, "generate",
                        lambda prompt, timeout_s=None:
                        seen.update(p=prompt, t=timeout_s) or "LIVE REPORT")
    body = api.get("/api/v1/alerts/ALT_000001/report").json()
    assert body == {"alert_id": "ALT_000001", "report": "LIVE REPORT",
                    "source": "gemini-live"}
    assert seen["t"] == 15
    assert "Elysium Care Clinic" in seen["p"] and "CASE SUMMARY" in seen["p"]


def test_report_live_failure_falls_back(api, monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(live, "generate", lambda prompt, timeout_s=None: None)
    assert api.get("/api/v1/alerts/ALT_000001/report").json()["source"] == "fallback"


def test_report_unknown_alert_404(api):
    assert api.get("/api/v1/alerts/ALT_999999/report").status_code == 404


# ---- chat ----

def test_chat_offline_reply_is_honest(api, monkeypatch):
    monkeypatch.delenv("NARRATION_LIVE", raising=False)
    body = api.post("/api/v1/alerts/ALT_000001/chat",
                    json={"messages": [{"role": "user", "text": "why high?"}]}).json()
    assert body["source"] == "fallback"
    assert "unavailable" in body["reply"]


def test_chat_live_prompt_is_context_bound(api, monkeypatch):
    _enable(monkeypatch)
    seen = {}
    monkeypatch.setattr(live, "generate",
                        lambda prompt, timeout_s=None:
                        seen.update(p=prompt) or "Because of the evidence.")
    body = api.post("/api/v1/alerts/ALT_000001/chat", json={"messages": [
        {"role": "user", "text": "first question"},
        {"role": "assistant", "text": "first answer"},
        {"role": "user", "text": "why is this scored high?"},
    ]}).json()
    assert body["reply"] == "Because of the evidence."
    assert body["source"] == "gemini-live"
    prompt = seen["p"]
    # the model sees the alert facts, the guardrail, and the transcript
    assert "Elysium Care Clinic" in prompt
    assert "never invent" in prompt
    assert "INVESTIGATOR: why is this scored high?" in prompt
    assert prompt.rstrip().endswith("ANALYST:")


def test_chat_validation(api):
    def post(payload):
        return api.post("/api/v1/alerts/ALT_000001/chat", json=payload)
    assert post({"messages": []}).status_code == 422
    assert post({"messages": [{"role": "user", "text": ""}]}).status_code == 422
    assert post({"messages": [{"role": "system", "text": "x"}]}).status_code == 422
    # last message must be the user's
    assert post({"messages": [{"role": "user", "text": "a"},
                              {"role": "assistant", "text": "b"}]}).status_code == 422
    assert post({"messages": [{"role": "user", "text": "x" * 2001}]}).status_code == 422


def test_chat_unknown_alert_404(api):
    assert api.post("/api/v1/alerts/ALT_999999/chat",
                    json={"messages": [{"role": "user", "text": "hi"}]}).status_code == 404
