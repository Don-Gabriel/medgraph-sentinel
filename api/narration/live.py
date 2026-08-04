"""Live narration via the Gemini API (ADR-037 — branch-only feature).

Tiering (INTERFACES §6, amended by ADR-037): when explicitly enabled, the
narration endpoint tries ONE live call first; on any failure — no key, no
network, quota, bad model name, malformed response, timeout — it returns
None and the caller falls through to the committed cache (ADR-032) and
then the deterministic template. The live tier can therefore never make
the endpoint slower than ~5 s or break it.

Stdlib-only on purpose (DAY2_PLAYBOOK Drill B shape, no new dependency):
one urllib POST with a hard timeout. Endpoint + payload shape verified
against ai.google.dev REST docs on 2026-08-05 (hard rule 2):
POST /v1beta/models/{model}:generateContent, header `x-goog-api-key`,
body {"contents":[{"parts":[{"text": ...}]}]}, text at
candidates[0].content.parts[0].text.
"""
import json
import logging
import os
import urllib.request

log = logging.getLogger("medgraph.api")

API_URL = ("https://generativelanguage.googleapis.com"
           "/v1beta/models/{model}:generateContent")
DEFAULT_MODEL = "gemini-3.5-flash"  # override with GEMINI_MODEL if renamed
TIMEOUT_S = 5  # contract ceiling — INTERFACES §6

# Read env per-call, not at import: tests monkeypatch, and a .env change
# takes effect on container restart without code reload ordering issues.


def enabled() -> bool:
    return (os.environ.get("NARRATION_LIVE", "").strip().lower()
            in ("1", "true", "yes")
            and bool(os.environ.get("GEMINI_API_KEY", "").strip()))


def generate(prompt: str) -> str | None:
    """One generateContent call; None on ANY failure so the caller falls
    back. Never raises."""
    try:
        model = os.environ.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL
        req = urllib.request.Request(
            API_URL.format(model=model),
            data=json.dumps(
                {"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "x-goog-api-key": os.environ["GEMINI_API_KEY"].strip()},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            body = json.load(resp)
        text = body["candidates"][0]["content"]["parts"][0]["text"].strip()
        return text or None
    except Exception as exc:  # noqa: BLE001 — degrade, never break the demo
        log.warning("live narration failed (%s: %s) — falling back to cache",
                    type(exc).__name__, exc)
        return None
