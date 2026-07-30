"""Narration cache builder — committed data, ZERO API calls (ADR-032).

The ADR-010 design (one live Claude API call per alert) is superseded:
there is no API key and no budget, ever. Instead the ADR-029 pattern
applies to narration too — it is a build-time artifact, produced once by
an assistant working session applying the SAME canonical prompt template
a live call would have used, reviewed, and committed. The demo serves
files; nothing generates.

Two modes, both deterministic:

    python -m api.narration.build --export-inputs prompts.jsonl
        Dump one JSON line per alert (id order): the composed prompt plus
        the bare facts. The assistant session writes narrations FROM these
        prompts, so tone and structure stay uniform across all alerts.

    python -m api.narration.build --import-texts a.json [b.json ...]
        Read {alert_id: text} maps, require EXACT coverage of the graph's
        alert ids (missing or extra ids abort — partial caches are the
        ADR-018 failure mode), then write api/narration_cache/<id>.json
        with the prompt_sha256 of the canonical prompt. Re-import over an
        unchanged graph is byte-identical.

Nothing here reads data/ground_truth/ — prompts are composed from the
alert, its summary_params, and implicated entities only (INTERFACES §8).
"""
import argparse
import hashlib
import json
import sys

from api import narration
from api.graph import get_driver

# Recorded in every cache entry. "pre-generated" is the honest label: a
# Claude model wrote the text, at build time, in a reviewed session — never
# live, never on the venue machine.
MODEL_TAG = "claude-fable-5 (assistant session, pre-generated)"

PROMPT_HEADER = (
    "You are writing the analyst narration for one fraud alert in a "
    "medical-tourism claims intelligence console. Audience: an insurance "
    "investigator who has not seen the graph. Write 4-7 sentences of "
    "plain, factual prose: (1) what pattern fired and the concrete "
    "numbers behind it; (2) why this combination is suspicious rather "
    "than each fact alone; (3) one honest alternative explanation or "
    "limitation; (4) the next investigative step. No headings, no lists, "
    "no hedging boilerplate, no invented facts beyond the data below.\n"
)


def _q(session, cypher: str, **params) -> list[dict]:
    return [dict(r) for r in session.run(cypher, **params)]


def fetch_alert_facts(session) -> list[dict]:
    """Alert + summary_params + implicated (id/type/label/role), id order.
    Mirrors the detail endpoint's data, composed independently so the
    builder has no FastAPI dependency."""
    alerts = _q(session, (
        "MATCH (a:Alert) RETURN a.id AS id, a.typology AS typology, "
        "a.score AS score, a.severity AS severity, "
        "a.summary_params AS summary_params ORDER BY a.id"))
    for alert in alerts:
        alert["summary_params"] = json.loads(alert["summary_params"] or "{}")
        rows = _q(session, (
            "MATCH (a:Alert {id: $id})-[r:IMPLICATES]->(n) "
            "RETURN coalesce(n.id, n.code) AS id, labels(n)[0] AS type, "
            "coalesce(n.name, n.full_name, n.code, n.id) AS label, "
            "r.role AS role ORDER BY role, id"), id=alert["id"])
        alert["implicated"] = rows
    return alerts


def compose_prompt(alert: dict) -> str:
    """The canonical template. Byte-stable for a given alert: this string
    is what prompt_sha256 commits to, and what the writing session reads."""
    lines = [PROMPT_HEADER]
    lines.append(f"ALERT {alert['id']} | typology {alert['typology']} | "
                 f"score {alert['score']} ({alert['severity']})")
    lines.append("EVIDENCE NUMBERS (summary_params):")
    for key in sorted(alert["summary_params"]):
        lines.append(f"  {key} = {json.dumps(alert['summary_params'][key])}")
    lines.append("IMPLICATED ENTITIES (role | type | label | id):")
    for ent in alert["implicated"][:40]:  # prompt stays bounded; the fan
        lines.append(f"  {ent['role']} | {ent['type']} | {ent['label']} | "
                     f"{ent['id']}")
    if len(alert["implicated"]) > 40:
        lines.append(f"  ... and {len(alert['implicated']) - 40} more of "
                     "the same roles")
    return "\n".join(lines) + "\n"


def export_inputs(out_path: str) -> int:
    with get_driver().session() as session:
        alerts = fetch_alert_facts(session)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        for alert in alerts:
            fh.write(json.dumps({
                "alert_id": alert["id"], "typology": alert["typology"],
                "severity": alert["severity"], "score": alert["score"],
                "prompt": compose_prompt(alert),
            }, sort_keys=True) + "\n")
    print(f"build: exported {len(alerts)} prompts -> {out_path}")
    return 0


def import_texts(paths: list[str]) -> int:
    texts: dict[str, str] = {}
    for path in paths:
        part = json.loads(open(path, encoding="utf-8").read())
        overlap = texts.keys() & part.keys()
        if overlap:
            print(f"build: duplicate alert ids across files: {sorted(overlap)[:5]}",
                  file=sys.stderr)
            return 2
        texts.update(part)

    with get_driver().session() as session:
        alerts = fetch_alert_facts(session)
    graph_ids = {a["id"] for a in alerts}
    missing, extra = graph_ids - texts.keys(), texts.keys() - graph_ids
    empty = [i for i, t in texts.items() if not t or not t.strip()]
    if missing or extra or empty:
        print(f"build: REFUSING partial/dirty cache - missing={sorted(missing)[:5]} "
              f"extra={sorted(extra)[:5]} empty={empty[:5]}", file=sys.stderr)
        return 1

    narration.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for alert in alerts:
        entry = {
            "alert_id": alert["id"],
            "text": texts[alert["id"]].strip(),
            "model": MODEL_TAG,
            "prompt_sha256": hashlib.sha256(
                compose_prompt(alert).encode("utf-8")).hexdigest(),
        }
        path = narration.CACHE_DIR / f"{alert['id']}.json"
        path.write_text(json.dumps(entry, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8", newline="\n")
    print(f"build: wrote {len(alerts)} cache entries -> {narration.CACHE_DIR}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m api.narration.build")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--export-inputs", metavar="OUT_JSONL")
    group.add_argument("--import-texts", nargs="+", metavar="TEXTS_JSON")
    args = parser.parse_args(argv)
    if args.export_inputs:
        return export_inputs(args.export_inputs)
    return import_texts(args.import_texts)


if __name__ == "__main__":
    sys.exit(main())
