"""Alert list/detail/PATCH/narration endpoint tests against the fake Neo4j
session (tests/conftest.py) — INTERFACES §6 semantics: filters, pagination
edges, severity ordering, server-composed titles, 404/422 shapes, and the
cache-first narration with deterministic fallback (ADR-010)."""
import json

import pytest

from api import narration
from api.alerts import (Q_ALERT_COUNT, Q_ALERT_IMPLICATED, Q_ALERT_LIST,
                        Q_ALERT_ONE, Q_ALERT_PATCH)
from api.narration.fallback import fallback_text
from api.titles import compose_title

# ---- fixture data: one alert per shipping typology + one unknown one ----

ALERTS = [
    {"id": "ALT_000001", "typology": "ghost_clinic", "rule_version": "1.0",
     "score": 91.5, "severity": "high", "status": "new", "note": "",
     "created_at": "2026-07-30T12:47:37Z",
     "summary_params": json.dumps({
         "clinic_name": "Elysium Care Clinic", "claim_count": 132,
         "bed_count": 0, "registration_age_years": 1.2, "inflow_share": 0.94,
         "payout_share": 0.97, "distinct_doctors": 2})},
    {"id": "ALT_000002", "typology": "credential_laundering",
     "rule_version": "1.0", "score": 88.0, "severity": "high",
     "status": "new", "note": "", "created_at": "2026-07-30T12:47:37Z",
     "summary_params": json.dumps({
         "signal": "shared_license", "license_no": "MC-TR-88231",
         "holder_count": 3, "issuing_countries": ["TR", "AE"],
         "actively_billing_holders": 2})},
    {"id": "ALT_000003", "typology": "kickback_ring", "rule_version": "1.0",
     "score": 60.4, "severity": "medium", "status": "reviewed",
     "note": "checked", "created_at": "2026-07-30T12:47:37Z",
     "summary_params": json.dumps({
         "broker_id": "BRK_000017", "clinic_id": "CLI_000591",
         "clinic_name": "Howell Clinic", "pair_claims": 54,
         "pair_amount_usd": 812345.5, "broker_share": 0.806,
         "clinic_share": 0.41, "shell_paths": 2,
         "shell_amount_usd": 40000.0})},
    {"id": "ALT_000004", "typology": "impossible_travel",
     "rule_version": "1.0", "score": 82.0, "severity": "high",
     "status": "dismissed", "note": "", "created_at": "2026-07-30T12:47:37Z",
     "summary_params": json.dumps({
         "passport_shared": True, "identity_count": 3,
         "impossible_pairs": 2, "min_gap_days": 0,
         "pairs": [{"claims": ["CLM_0000001", "CLM_0000002"],
                    "countries": ["TH", "TR"],
                    "dates": ["2026-02-01", "2026-02-01"], "gap_days": 0}]})},
    # circular_payment became a real typology (ADR-038), so the unknown-
    # typology degradation case uses a genuinely unshipped Day-2 shape
    {"id": "ALT_000005", "typology": "sanctioned_accreditor",  # Day-2 shape
     "rule_version": "0.1", "score": 33.0, "severity": "low",
     "status": "new", "note": "", "created_at": "2026-07-30T12:47:37Z",
     "summary_params": json.dumps({"accreditor_count": 2})},
]

IMPLICATED = {
    "ALT_000001": [
        {"id": "ACC_000944", "type": "PaymentAccount", "role": "hub_account",
         "props": {"id": "ACC_000944", "bank_name": "First Fictional"}},
        {"id": "CLI_000217", "type": "Clinic", "role": "ghost_clinic",
         "props": {"id": "CLI_000217", "name": "Elysium Care Clinic",
                   "bed_count": 0}},
        {"id": "DOC_000012", "type": "Doctor", "role": "roster_doctor",
         "props": {"id": "DOC_000012", "full_name": "Dr. A. Invented"}},
        {"id": "TH", "type": "Country", "role": "treatment_country",
         "props": {"code": "TH", "name": "Thailand"}},
    ],
}

SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}


def install_alert_handlers(fake, store):
    """Fake the four alert queries over an in-memory list — same filter,
    sort and pagination semantics the Cypher implements."""

    def matches(a, p):
        if p.get("status") is not None and a["status"] != p["status"]:
            return False
        if p.get("typology") is not None and a["typology"] != p["typology"]:
            return False
        if p.get("severities") is not None and a["severity"] not in p["severities"]:
            return False
        return True

    def count(p):
        return [{"total": sum(1 for a in store if matches(a, p))}]

    def listing(p):
        rows = sorted((a for a in store if matches(a, p)),
                      key=lambda a: (-a["score"], a["id"]))
        page = rows[p["offset"]:p["offset"] + p["limit"]]
        return [{**a, "implicated_count": len(IMPLICATED.get(a["id"], []))}
                for a in page]

    def one(p):
        return [a for a in store if a["id"] == p["id"]]

    def implicated(p):
        return sorted(IMPLICATED.get(p["id"], []), key=lambda r: r["id"])

    def patch(p):
        for a in store:
            if a["id"] == p["id"]:
                if p["status"] is not None:
                    a["status"] = p["status"]
                if p["note"] is not None:
                    a["note"] = p["note"]
                return [{"id": a["id"]}]
        return []

    fake.handle(Q_ALERT_COUNT, count)
    fake.handle(Q_ALERT_LIST, listing)
    fake.handle(Q_ALERT_ONE, one)
    fake.handle(Q_ALERT_IMPLICATED, implicated)
    fake.handle(Q_ALERT_PATCH, patch)


@pytest.fixture
def store():
    return [dict(a) for a in ALERTS]  # fresh copies — PATCH tests mutate


@pytest.fixture
def api(client, fake_session, store):
    install_alert_handlers(fake_session, store)
    return client


# ---- list: envelope, sorting, filters, pagination ----

def test_list_envelope_sorted_by_score_desc(api):
    body = api.get("/api/v1/alerts").json()
    assert body["total"] == 5
    assert [i["id"] for i in body["items"]] == [
        "ALT_000001", "ALT_000002", "ALT_000004", "ALT_000003", "ALT_000005"]
    item = body["items"][0]
    assert item == {
        "id": "ALT_000001", "typology": "ghost_clinic", "rule_version": "1.0",
        "score": 91.5, "severity": "high", "status": "new", "note": "",
        "created_at": "2026-07-30T12:47:37Z",
        "title": "Ghost clinic pattern: Elysium Care Clinic",
        "implicated_count": 4,
    }
    assert "summary_params" not in item  # detail-only field


def test_list_filters_status_and_typology(api):
    body = api.get("/api/v1/alerts?status=reviewed").json()
    assert body["total"] == 1 and body["items"][0]["id"] == "ALT_000003"
    body = api.get("/api/v1/alerts?typology=ghost_clinic&status=new").json()
    assert [i["id"] for i in body["items"]] == ["ALT_000001"]
    # unknown typology filters to empty — NOT a 422 (Day-2 rules, ADR-008)
    body = api.get("/api/v1/alerts?typology=no_such_rule").json()
    assert body == {"total": 0, "items": []}


def test_list_min_severity_means_at_least(api):
    assert api.get("/api/v1/alerts?min_severity=high").json()["total"] == 3
    body = api.get("/api/v1/alerts?min_severity=medium").json()
    assert body["total"] == 4
    assert all(SEVERITY_ORDER[i["severity"]] >= 1 for i in body["items"])
    assert api.get("/api/v1/alerts?min_severity=low").json()["total"] == 5


def test_list_validation_422s(api):
    assert api.get("/api/v1/alerts?status=resolved").status_code == 422
    assert api.get("/api/v1/alerts?min_severity=critical").status_code == 422
    assert api.get("/api/v1/alerts?limit=201").status_code == 422
    assert api.get("/api/v1/alerts?limit=0").status_code == 422
    assert api.get("/api/v1/alerts?offset=-1").status_code == 422
    body = api.get("/api/v1/alerts?limit=201").json()
    assert isinstance(body["detail"], str)  # contract error shape, not a list


def test_list_pagination_edges(api):
    body = api.get("/api/v1/alerts?limit=2&offset=1").json()
    assert body["total"] == 5  # total ignores the page window
    assert [i["id"] for i in body["items"]] == ["ALT_000002", "ALT_000004"]
    assert api.get("/api/v1/alerts?limit=200&offset=999").json()["items"] == []


# ---- titles: one per typology, composed from summary_params ----

def test_titles_per_typology(api):
    titles = {i["id"]: i["title"]
              for i in api.get("/api/v1/alerts?limit=200").json()["items"]}
    assert titles == {
        "ALT_000001": "Ghost clinic pattern: Elysium Care Clinic",
        "ALT_000002": "Credential laundering: licence MC-TR-88231 held by 3 doctors",
        "ALT_000003": "Kickback ring: broker BRK_000017 and Howell Clinic",
        "ALT_000004": "Impossible travel: one passport, 3 patient identities",
        "ALT_000005": "Sanctioned accreditor alert",  # unknown typology degrades
    }


def test_title_composition_handles_malformed_params():
    assert compose_title("ghost_clinic", {}) == "Ghost clinic pattern: unnamed clinic"
    assert compose_title("credential_laundering",
                         {"signal": "jurisdiction_shopping+post_revocation_billing"}) \
        == "Credential laundering: post-revocation billing + jurisdiction shopping"
    assert compose_title("impossible_travel", {"passport_shared": False}) \
        == "Impossible travel: same-day claims in two countries"


# ---- detail ----

def test_detail_parses_summary_params_and_labels_implicated(api):
    body = api.get("/api/v1/alerts/ALT_000001").json()
    assert body["summary_params"]["claim_count"] == 132  # parsed, not a string
    assert body["title"] == "Ghost clinic pattern: Elysium Care Clinic"
    assert body["implicated_count"] == 4
    by_id = {e["id"]: e for e in body["implicated"]}
    # label fallback chain: name / full_name / code / id (INTERFACES §6)
    assert by_id["CLI_000217"]["label"] == "Elysium Care Clinic"
    assert by_id["DOC_000012"]["label"] == "Dr. A. Invented"
    assert by_id["TH"]["label"] == "Thailand"          # Country: name
    assert by_id["ACC_000944"]["label"] == "ACC_000944"  # no name → id
    assert by_id["CLI_000217"]["role"] == "ghost_clinic"
    assert set(by_id["CLI_000217"]) == {"id", "type", "label", "role"}


def test_detail_404_unknown_id(api):
    response = api.get("/api/v1/alerts/ALT_999999")
    assert response.status_code == 404
    assert response.json() == {"detail": "unknown alert ALT_999999"}


# ---- PATCH ----

def test_patch_status_and_note_roundtrip(api):
    body = api.patch("/api/v1/alerts/ALT_000001",
                     json={"status": "reviewed", "note": "no footprint"}).json()
    assert body["status"] == "reviewed" and body["note"] == "no footprint"
    assert body["id"] == "ALT_000001" and "implicated" in body  # full detail
    # note-only patch keeps status; empty string clears the note
    body = api.patch("/api/v1/alerts/ALT_000001", json={"note": ""}).json()
    assert body["status"] == "reviewed" and body["note"] == ""
    body = api.patch("/api/v1/alerts/ALT_000001", json={"status": "new"}).json()
    assert body["status"] == "new" and body["note"] == ""


def test_patch_validation_422s(api):
    assert api.patch("/api/v1/alerts/ALT_000001",
                     json={"status": "escalated"}).status_code == 422
    assert api.patch("/api/v1/alerts/ALT_000001",
                     json={"note": "x" * 2001}).status_code == 422
    assert api.patch("/api/v1/alerts/ALT_000001",
                     json={"note": "x" * 2000}).status_code == 200
    assert api.patch("/api/v1/alerts/ALT_000001", json={}).status_code == 422


def test_patch_404_unknown_id(api):
    assert api.patch("/api/v1/alerts/ALT_999999",
                     json={"status": "reviewed"}).status_code == 404


# ---- narration: cache-first, deterministic fallback ----

def test_narration_fallback_per_typology(api, tmp_path, monkeypatch):
    # isolate from the committed cache (81 real entries since ADR-032) —
    # this test exercises the TEMPLATE path, so it needs an empty cache dir
    monkeypatch.setattr(narration, "CACHE_DIR", tmp_path)
    cases = {
        "ALT_000001": ["Elysium Care Clinic", "132 claims", "0 beds",
                       "94%", "97%", "ghost-clinic"],
        "ALT_000002": ["MC-TR-88231", "3 different doctors", "TR, AE",
                       "credential-laundering"],
        "ALT_000003": ["BRK_000017", "54 claims", "$812,346", "Howell Clinic",
                       "81%", "2 money path(s)", "kickback"],
        "ALT_000004": ["3 patient identities", "TH", "TR", "2026-02-01",
                       "passport"],
        "ALT_000005": ["sanctioned accreditor", "accreditor_count=2"],  # generic template
    }
    for alert_id, needles in cases.items():
        body = api.get(f"/api/v1/alerts/{alert_id}/narration").json()
        assert body["alert_id"] == alert_id and body["source"] == "fallback"
        for needle in needles:
            assert needle in body["text"], (alert_id, needle, body["text"])


def test_narration_cache_hit(api, tmp_path, monkeypatch):
    monkeypatch.setattr(narration, "CACHE_DIR", tmp_path)
    (tmp_path / "ALT_000001.json").write_text(json.dumps({
        "alert_id": "ALT_000001", "text": "Cached narration text.",
        "model": "claude-opus-5", "prompt_sha256": "ab" * 32}),
        encoding="utf-8")
    body = api.get("/api/v1/alerts/ALT_000001/narration").json()
    assert body == {"alert_id": "ALT_000001", "text": "Cached narration text.",
                    "source": "claude-cached"}
    # other alerts still fall back — cache is strictly per alert id
    assert api.get("/api/v1/alerts/ALT_000002/narration").json()["source"] == "fallback"


def test_narration_malformed_cache_falls_back(api, tmp_path, monkeypatch):
    monkeypatch.setattr(narration, "CACHE_DIR", tmp_path)
    (tmp_path / "ALT_000001.json").write_text("not json {", encoding="utf-8")
    (tmp_path / "ALT_000002.json").write_text(
        json.dumps({"alert_id": "ALT_999999", "text": "wrong alert"}),
        encoding="utf-8")
    assert api.get("/api/v1/alerts/ALT_000001/narration").json()["source"] == "fallback"
    assert api.get("/api/v1/alerts/ALT_000002/narration").json()["source"] == "fallback"


def test_narration_404_only_for_unknown_alert(api):
    assert api.get("/api/v1/alerts/ALT_999999/narration").status_code == 404


def test_fallback_text_never_raises_on_garbage():
    for typology in ("ghost_clinic", "credential_laundering", "kickback_ring",
                     "impossible_travel", "brand_new_rule"):
        text = fallback_text(typology, {})
        assert isinstance(text, str) and text
        # values of the wrong type degrade, never raise (ADR-010 spirit)
        assert fallback_text(typology, {"pairs": "oops", "inflow_share": "x"})
