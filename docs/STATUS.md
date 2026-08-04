# STATUS — snapshot, not a log

**Updated:** 2026-08-03, consistency sweep + CI adoption · **Days to Day 1 (Aug 12): 9**

---

# 🔀 BRANCH `next/prediction-gemini` (2026-08-05 — read this block only on this branch)

**Everything below the branch block describes frozen `main` and stays
true there.** This branch (ADR-037) carries the Coimbatore-event upgrade
and must NOT merge into `main` before Aug 14:

- **Live narration tier (opt-in):** `NARRATION_LIVE=true` + `GEMINI_API_KEY`
  in `.env` → live Gemini call first (5 s ceiling), cache then template as
  fallback; `source: gemini-live`. Flag unset = frozen behaviour exactly.
  **Verified live 2026-08-05 with the owner's free-tier key:** real
  generation served with honest labeling; model measured and pinned to
  `gemini-3.5-flash-lite` (0.9 s; plain flash overran the 5 s ceiling on
  the full prompt; 2.5-family names 404).
- **Typology 4 shipped:** claim-mill overlay (`data/scenarios/
  claim_mill_demo.yaml`, `clone_pack` journeys) + `template_cloning` rule.
  **82 alerts** now (81 untouched + ALT_000082, 94.3 high). Calibration on
  the honest economy: 0 alerts. Old cache entries byte-identical.
- **Forecast:** `GET /api/v1/forecast` + console strip (least-squares
  projection, honestly labeled).
- Tests **89**, ruff clean, frontend builds. Drill-container calibration
  records in ADR-037.
- On the lead machine: branch stack runs as compose project
  `medgraph-next`, images `:next`, neo4j 17474/17687, api 8001, frontend
  5174 (uncommitted `docker-compose.override.yml` + local `.env`) — the
  frozen `:demo` images, volumes, and the running demo stack are untouched.
- Remaining on this branch: real-key live-narration smoke test (owner),
  E2E boot verification of the `:next` stack, pitch-line updates for the
  Coimbatore rounds ("4 of 6 designed typologies shipped; here is the
  fifth's spec" no longer applies — it is now 5 of 6).

---

---

# ⛔ CODE IS FROZEN (2026-07-30)

**The build is done. From this moment, changes are permitted for exactly
three reasons:**

1. **Cold-start findings** — whatever the Aug 4–5 offline drill breaks.
2. **Rehearsal breakage** — something that reads wrong or fails when said
   aloud, or a demo-path defect found while practising.
3. **Factual corrections** — a wrong number or stale claim in a doc.

**Everything else is out of scope, including "just polishing".** No new
features, no refactors, no visual tweaks, no extra typologies, no
"while I'm in here". If you find yourself editing code for any reason not
on that list of three, stop — the remaining risk in this project is
delivery, not software.

Unfreezing the dataset is a separate, harder rule (ADR-031/032): any
regeneration re-runs the whole ADR-018 chain including re-narration, and
after Aug 8 it is a demo-blocker emergency only.

---

## What exists (all merged to main, all verified running)

| layer | state |
|---|---|
| Generator | Frozen seed-42 economy + overlays + planted cells (ADR-031). Byte-identical on re-run. |
| Graph | Neo4j 5.26 + GDS 2.13.11, our own image with GDS baked in (ADR-026). Seeds in ~21 s. |
| Detection | 4 typologies, config-driven registry, calibrated on the honest economy only (ADR-030); centrality benchmarked out (ADR-028). |
| Alerts | **81**, precomputed and committed as CSV data — no clone ever runs detection (ADR-029). |
| Narration | **81/81 pre-generated and committed**, zero API calls ever (ADR-032). `/health` guards completeness by alert-id set. |
| API | Full INTERFACES §6 surface, 300-node subgraph cap. |
| Console | Queue + Cytoscape evidence view + case file + disposition; projector-legibility pass done (ADR-035). |
| Demo backup | `screenshot-deck/` (7 beats, 1920×1080) + `demo-recording.webm` (53.7 s, 5.9 MB), both committed. |
| Offline bundle | Staged at `C:\WorkSpace\Private\medgraph-demo-usb\`; drill script `docs/COLD_START.md`. **Restage from final main after PR #16 merges** (freshness check in COLD_START). |
| Tests | **70 passing.** |
| CI | GitHub Actions (ADR-036): ruff + pytest + frontend build on push-to-main and PRs; rule set pinned so the gate never touches frozen code. |

## Evaluation results (final — do not restate from memory, read them)

- **Honest economy:** zero medium-or-high alerts on every rule.
- **Dev set:** planted cells 3/3 (ghost) and 3/3 (credential), all `high`;
  impossible-travel groups 3/3 `high`; kickback precision 1.0, broker
  recall 6/13.
- **Held-out (one shot, pre-registered):** 5 scenarios · 8 legs expected ·
  **5 detected · 3 missed · 2 root causes**; all 5 scenarios raised at
  least one alert. Identical numbers in PITCH.md, README.md and
  HELDOUT_COMMITMENT.md — change one, change all three.

## What remains — rehearsal, not building

1. **Rehearsal.** The pitch has never been said out loud. This is now the
   single largest risk in the project. Kit is ready: PITCH.md is a runnable
   script with cumulative timestamps, a self-scoring rubric, 15 ranked
   questions, and 60-second / 3-minute versions.
2. **Cold start (Aug 4–5, owner-physical).** docs/COLD_START.md, phases
   1–6. Only the USB walk and the network adapter are human steps.
3. **Day-2 drills.** Three turnkey cards in DAY2_PLAYBOOK.md.
4. **Two freeze-formality commits** (Aug 6 detection, Aug 8 integration),
   each recording that nothing changed — which is the point.
5. **Repo public**, Aug 11 evening.

## Decisions awaiting a human

- (none — OQ #7 resolved by owner direction 2026-08-03, ADR-036)

## Actions awaiting a human

- (none)

## End-to-end verification, 2026-08-03 (software half of the cold-start drill)

PR #16 merged; CI green on main (34 s). Then from merged main: all three
images rebuilt → `docker compose down -v` (volume wiped) → `up -d` →
**seed exit 0, 52,071 nodes / 199,349 rels, all 33 manifest counts match,
17.9 s** → `/health` ok with narration 81/81 by id-set → console verified
in a real browser: 81-alert queue, typology filters (61/9/6/5),
impossible-travel evidence view (19 nodes/36 edges, halos), narration
panel labeled "pre-generated AI narration", disposition PATCH round-trip
(reset to `new` afterwards — queue is clean), **zero console errors**.
USB bundle restaged from final main same day. Still owner-physical: the
USB-stick walk on a cold machine and the network-adapter-off run
(COLD_START phases 1–6).
