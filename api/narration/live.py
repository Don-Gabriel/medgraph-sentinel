"""Optional live narration via the Gemini REST API.

**Off unless explicitly switched on.** The demo path is unchanged: the
committed cache (ADR-032) answers all 81 alerts, so with a complete cache
this module is never reached even when enabled. It exists for the case the
cache misses — a newly detected alert, or a dataset regenerated after the
cache was built — where a live call beats the deterministic template.

Two independent switches, both required (belt and braces, because the venue
is assumed offline — ADR-019):

    NARRATION_LIVE=1        explicit opt-in; absent/0/false = never call
    GEMINI_API_KEY=<key>    supplied via .env, never committed (hard rule 7)

Optional: GEMINI_MODEL (default below), NARRATION_LIVE_TIMEOUT_S.

The prompt is `build.compose_prompt` — the SAME canonical template the
committed cache was written from — so a live narration reads like a cached
one instead of drifting in tone. Nothing here reads data/ground_truth/
(INTERFACES §8): the prompt is composed from the alert, its summary_params
and its implicated entities only.

stdlib urllib on purpose: no new dependency in pyproject, so the offline
image is byte-for-byte what it was. Every failure path returns None and the
caller falls through to the template — this module can never raise, and can
never make the API 500 (INTERFACES §6).

REST contract VERIFIED against ai.google.dev/gemini-api (fetched 2026-09-08):
POST {endpoint}, header `x-goog-api-key`, body {"contents":[{"parts":[
{"text": ...}]}]}, reply candidates[0].content.parts[*].text.
"""
import json
import logging
import os
import urllib.error
import urllib.request

from api.narration.build import compose_prompt

log = logging.getLogger("medgraph.api")

ENDPOINT = ("https://generativelanguage.googleapis.com/v1beta/"
            "models/{model}:generateContent")
# A rolling alias, deliberately NOT a pinned version — the one place in this
# repo where pinning is the wrong call. Verified live 2026-09-08: the pinned
# `gemini-2.5-flash-lite` from Google's own docs returns HTTP 404 "no longer
# available to new users", and so does gemini-2.5-flash. A pinned model here
# is a time bomb that fires as a silent fallback-to-template, months after
# the commit. The alias tracks the current lite flash model instead.
# Override per-deployment with GEMINI_MODEL.
DEFAULT_MODEL = "gemini-flash-lite-latest"
DEFAULT_TIMEOUT_S = 8.0
_TRUE = {"1", "true", "yes", "on"}


def is_enabled() -> bool:
    """Both switches, read at call time so tests can flip them per-case."""
    return (os.environ.get("NARRATION_LIVE", "").strip().lower() in _TRUE
            and bool(os.environ.get("GEMINI_API_KEY", "").strip()))


def model_name() -> str:
    return os.environ.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL


def _timeout_s() -> float:
    try:
        return float(os.environ.get("NARRATION_LIVE_TIMEOUT_S", ""))
    except ValueError:
        return DEFAULT_TIMEOUT_S


def _extract_text(payload: dict) -> str | None:
    """candidates[0].content.parts[*].text, joined. Any shape surprise ->
    None: a partial or reshaped reply must degrade, not raise."""
    try:
        parts = payload["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError):
        return None
    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
    return text.strip() or None


def generate(prompt: str) -> str | None:
    """One Gemini call. Returns the narration text, or None on ANY failure
    (disabled, network, auth, timeout, malformed reply, blocked content)."""
    if not is_enabled():
        return None
    key = os.environ["GEMINI_API_KEY"].strip()
    url = ENDPOINT.format(model=model_name())
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    try:
        with urllib.request.urlopen(request, timeout=_timeout_s()) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Read the body: Google puts the ACTIONABLE reason there, not in the
        # status line. A retired model answers 404 "no longer available to
        # new users. Please update your code to use models/X" while still
        # appearing in ListModels — diagnosing that from "404 Not Found"
        # alone cost two round trips on 2026-09-08 (ADR-037). The key is
        # never echoed: only Google's message is logged.
        detail = ""
        try:
            detail = json.loads(exc.read().decode("utf-8"))\
                .get("error", {}).get("message", "")[:200]
        except Exception:
            detail = exc.reason or ""
        log.warning("gemini narration HTTP %s: %s", exc.code, detail)
        return None
    except Exception as exc:  # timeout, DNS, TLS, bad JSON — all "degrade"
        log.warning("gemini narration call failed: %s", exc)
        return None
    text = _extract_text(payload)
    if text is None:
        log.warning("gemini narration returned no usable text")
    return text


def narrate_alert(alert_id: str, typology: str, score, severity: str,
                  params: dict, implicated: list[dict]) -> str | None:
    """Compose the canonical prompt for one alert and generate. Same
    signature shape the cache builder feeds compose_prompt, so the two paths
    cannot drift apart."""
    prompt = compose_prompt({
        "id": alert_id, "typology": typology, "score": score,
        "severity": severity, "summary_params": params or {},
        "implicated": implicated,
    })
    return generate(prompt)
