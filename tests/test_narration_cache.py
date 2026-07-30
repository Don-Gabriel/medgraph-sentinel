"""Narration-cache completeness guard (ADR-018 tightened by ADR-032) and
builder prompt determinism. No database needed."""
import json

from api import main as api_main
from api import narration
from api.narration.build import PROMPT_HEADER, compose_prompt

ALERT = {
    "id": "ALT_000001", "typology": "ghost_clinic", "score": 84.9,
    "severity": "high",
    "summary_params": {"claim_count": 56, "inflow_share": 0.946},
    "implicated": [
        {"id": "CLI_000602", "type": "Clinic",
         "label": "Compton Medical Centre", "role": "ghost_clinic"},
    ],
}


def _write_cache(dirpath, ids):
    for alert_id in ids:
        (dirpath / f"{alert_id}.json").write_text(
            json.dumps({"alert_id": alert_id, "text": "t", "model": "m",
                        "prompt_sha256": "0" * 64}), encoding="utf-8")


def _status_with(monkeypatch, tmp_path, graph_ids, cache_ids):
    monkeypatch.setattr(narration, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(api_main, "_alert_ids",
                        lambda: set(graph_ids) if graph_ids is not None else None)
    _write_cache(tmp_path, cache_ids)
    return api_main.narration_cache_status()


def test_exact_coverage_matches(monkeypatch, tmp_path):
    s = _status_with(monkeypatch, tmp_path,
                     ["ALT_000001", "ALT_000002"], ["ALT_000001", "ALT_000002"])
    assert s["match"] is True and s["missing"] == 0
    assert s["alerts"] == 2 and s["cached"] == 2


def test_equal_counts_wrong_ids_fail(monkeypatch, tmp_path):
    # the ADR-032 tightening: a cache from a DIFFERENT detection run has the
    # right size and must still fail loudly
    s = _status_with(monkeypatch, tmp_path,
                     ["ALT_000001", "ALT_000002"], ["ALT_000008", "ALT_000009"])
    assert s["match"] is False and s["missing"] == 2


def test_missing_entries_fail(monkeypatch, tmp_path):
    s = _status_with(monkeypatch, tmp_path,
                     ["ALT_000001", "ALT_000002"], ["ALT_000001"])
    assert s["match"] is False and s["missing"] == 1


def test_unreachable_graph_fails(monkeypatch, tmp_path):
    s = _status_with(monkeypatch, tmp_path, None, ["ALT_000001"])
    assert s["match"] is False and s["alerts"] == 0


def test_health_endpoint_reports_completeness(monkeypatch, tmp_path):
    # endpoint-level regression test: health() must survive the ADR-032
    # helper rename and report ok/degraded off the id-set check
    from fastapi.testclient import TestClient
    monkeypatch.setattr(narration, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(api_main, "_query_one", lambda c: {"ok": 1})
    monkeypatch.setattr(api_main, "_alert_ids", lambda: {"ALT_000001"})
    client = TestClient(api_main.app)

    body = client.get("/api/v1/health").json()
    assert body["status"] == "degraded" and body["narration_cache"]["missing"] == 1

    _write_cache(tmp_path, ["ALT_000001"])
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok" and body["alert_count"] == 1
    assert body["narration_cache"] == {"alerts": 1, "cached": 1,
                                       "match": True, "missing": 0}


def test_compose_prompt_deterministic_and_templated():
    p1, p2 = compose_prompt(ALERT), compose_prompt(ALERT)
    assert p1 == p2  # prompt_sha256 relies on byte stability
    assert p1.startswith(PROMPT_HEADER)
    assert "claim_count = 56" in p1 and "ghost_clinic" in p1
    # summary keys are emitted sorted, so dict order can't change the hash
    reordered = dict(ALERT, summary_params={"inflow_share": 0.946,
                                            "claim_count": 56})
    assert compose_prompt(reordered) == p1
