"""AI-assist endpoints (ADR-038): case-file report + case chat.

Both are click-initiated, context-bound uses of the same live adapter as
narration (api/narration/live.py). The model NEVER gets database access —
it answers only from the canonical alert facts the server composes
(compose_prompt: alert + summary_params + implicated entities, no ground
truth, hard rule 5). Both degrade honestly: the report falls back to a
deterministic template assembled from the same facts, the chat says
plainly that the live tier is unavailable. Free-tier posture: nothing
here is called automatically — one click, one API call, and a rate-limit
429 simply lands in the fallback path.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.alerts import Q_ALERT_IMPLICATED, Q_ALERT_ONE
from api.graph import display_label, get_session, run_query
from api.narration import live
from api.narration.build import compose_prompt
from api.narration.fallback import fallback_text
from api.titles import compose_title, parse_summary_params

router = APIRouter(prefix="/api/v1")

ASSIST_TIMEOUT_S = 15  # click-initiated: the user is watching a spinner

REPORT_INSTRUCTION = (
    "\nWrite a Special Investigation Unit case-file report from the facts "
    "above, as PLAIN TEXT (no markdown symbols). Structure it with these "
    "uppercase section headings, each on its own line: CASE SUMMARY, "
    "KEY EVIDENCE, ASSESSMENT, RECOMMENDED ACTIONS, LIMITATIONS. Keep it "
    "under 350 words, factual, and grounded ONLY in the data above — no "
    "invented names, amounts, dates, or regulations. In LIMITATIONS state "
    "honestly what this alert alone cannot prove.\n"
)

CHAT_INSTRUCTION = (
    "\nYou are the analyst assistant for this ONE alert. Answer the "
    "investigator's questions using ONLY the facts above and the "
    "conversation so far. If the facts above do not contain the answer, "
    "say exactly that and suggest which record to pull — never invent "
    "entities, numbers, or events. Keep answers under 120 words, plain "
    "prose.\n\nCONVERSATION:\n"
)

CHAT_OFFLINE_REPLY = (
    "The live AI tier is unavailable right now (offline or rate-limited). "
    "The pre-generated narration and the evidence panel contain this "
    "alert's full facts; ask again once the connection is back."
)


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    text: str = Field(min_length=1, max_length=2000)


class ChatBody(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=16)


def _alert_facts(session, alert_id: str) -> dict:
    rows = run_query(session, Q_ALERT_ONE, id=alert_id)
    if not rows:
        raise HTTPException(status_code=404, detail=f"unknown alert {alert_id}")
    implicated = [
        {"id": r["id"], "type": r["type"],
         "label": display_label(r["props"], r["id"]), "role": r["role"]}
        for r in run_query(session, Q_ALERT_IMPLICATED, id=alert_id)
    ]
    return {
        "id": alert_id, "typology": rows[0]["typology"],
        "score": rows[0]["score"], "severity": rows[0]["severity"],
        "summary_params": parse_summary_params(rows[0]["summary_params"]),
        "implicated": implicated,
    }


def _template_report(alert: dict) -> str:
    """Deterministic fallback: the same sections, assembled from the same
    facts — the report feature works fully offline (ADR-032 spirit)."""
    title = compose_title(alert["typology"], alert["summary_params"])
    evidence = "\n".join(
        f"  - {k} = {v}" for k, v in sorted(alert["summary_params"].items())
        if isinstance(v, (str, int, float, bool)))
    entities = "\n".join(
        f"  - {e['role']}: {e['label']} ({e['id']})"
        for e in alert["implicated"][:15])
    more = (f"\n  ... and {len(alert['implicated']) - 15} more"
            if len(alert["implicated"]) > 15 else "")
    return (
        f"CASE SUMMARY\n{title}. Alert {alert['id']}, severity "
        f"{alert['severity']} (score {alert['score']}).\n\n"
        f"KEY EVIDENCE\n{evidence}\n\nIMPLICATED ENTITIES\n{entities}{more}\n\n"
        f"ASSESSMENT\n{fallback_text(alert['typology'], alert['summary_params'])}\n\n"
        f"RECOMMENDED ACTIONS\nReview the evidence subgraph, verify the "
        f"implicated entities against source records, and record a "
        f"disposition with notes.\n\n"
        f"LIMITATIONS\nThis report is assembled from detection output on "
        f"synthetic data; it is a lead for investigation, not a finding "
        f"of fraud."
    )


@router.get("/alerts/{alert_id}/report")
def alert_report(alert_id: str, session=Depends(get_session)) -> dict:
    alert = _alert_facts(session, alert_id)
    if live.enabled():
        text = live.generate(compose_prompt(alert) + REPORT_INSTRUCTION,
                             timeout_s=ASSIST_TIMEOUT_S)
        if text:
            return {"alert_id": alert_id, "report": text,
                    "source": "gemini-live"}
    return {"alert_id": alert_id, "report": _template_report(alert),
            "source": "fallback"}


@router.post("/alerts/{alert_id}/chat")
def alert_chat(alert_id: str, body: ChatBody,
               session=Depends(get_session)) -> dict:
    if body.messages[-1].role != "user":
        raise HTTPException(status_code=422,
                            detail="last message must be from the user")
    alert = _alert_facts(session, alert_id)
    if live.enabled():
        transcript = "\n".join(
            f"{'INVESTIGATOR' if m.role == 'user' else 'ANALYST'}: {m.text}"
            for m in body.messages)
        prompt = (compose_prompt(alert) + CHAT_INSTRUCTION + transcript
                  + "\nANALYST:")
        text = live.generate(prompt, timeout_s=ASSIST_TIMEOUT_S)
        if text:
            return {"alert_id": alert_id, "reply": text,
                    "source": "gemini-live"}
    return {"alert_id": alert_id, "reply": CHAT_OFFLINE_REPLY,
            "source": "fallback"}
