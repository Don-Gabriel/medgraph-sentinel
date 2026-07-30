# Pitch — 10 Minutes, Day 1 (Aug 12)

Version 1 (planning phase). Revise after M3 when the real demo exists; final
version locks Aug 11 after rehearsal ×3. Timings are hard budgets — the timer
runs at every rehearsal. Speaker names follow DEFENCE_AREAS (provisional).

## Minute-by-minute

| time | beat | speaker | content |
|---|---|---|---|
| 0:00–1:00 | Hook | Don Gabriel | One patient journey, five record-keepers, nobody sees the chain. "Every record looks fine. The fraud is only visible in the relationships." One sentence on what we built. |
| 1:00–2:00 | The insight | Mary Vivitha | Per-claim detection catches bad claims, never bad *networks*; organised fraud is always a network. Fraud-is-relational ⇒ graph database. Name the four shipping typologies in one breath; "two more are specified and waiting" (ADR-024 — roadmap, said with confidence, not apology). |
| 2:00–2:45 | What we built | Poonkundran | 30-second architecture: synthetic economy → Neo4j graph (50k nodes) → detection layer → investigator console. "docker compose up, three minutes, everything you're about to see runs offline on this laptop." |
| 2:45–6:30 | **Live demo** | Pavithra (drives) + Mary (narrates findings) | The click path below. |
| 6:30–7:45 | How we know it works | Vijayalakshmi | The circularity defense as a *feature*: emergent vs planted fraud, frozen detection spec, hash-committed held-out scenarios, evaluated once. Show the precision/recall slide **including misses**. Use the claim branch that OQ #12 resolved to (below) — never the stronger one on spec. State the limits unprompted (synthetic ≠ real world). |
| 7:45–8:45 | Architecture & honest limits | Don Gabriel | Stack choices in three sentences (why Neo4j, why batch alerts, why one LLM call). What production needs that this doesn't: consortium data sharing, entity resolution, RBAC. "We know where the prototype ends." |
| 8:45–10:00 | Who buys it + close | Pavithra | Insurers/TPAs/accreditors/health authorities; the wedge is the TPA. Close on the team: five people, every module explainable by the person you point at. Invite questions. |

## Demo click path (draft — finalize against the real dataset Aug 7)

1. Console open pre-loaded (never boot live). Header stats: ~50k nodes, ~140k
   relationships, alert counts by typology. *One breath on synthetic data:
   "fictional entities, real corridor economics."*
2. Alert queue sorted by score. Point at the spread of typologies. Filter to
   `ghost_clinic`, open the top alert.
3. Evidence subgraph: the clinic, its single feeder broker, the payout
   account hub, the claim fan. Mary narrates the structure ("every one of
   these claims looks fine alone — watch what they share").
4. Narration panel: the plain-English explanation. Say it's a cached Claude
   call with an offline fallback — honesty beats magic.
5. Mark the alert `reviewed` with a note — the investigator workflow beat.
6. Second alert, different family: `impossible_travel` — one identity on two
   operating tables in two countries days apart (structural, not
   statistical — the contrast with alert #1 shows range, and it lands in
   one sentence).
7. Back to queue; point at an alert we'll *dismiss* live as a documented
   false positive (standardized dental package) — showing FP awareness is
   worth more than a seventh feature.

Fallback path: if anything hangs, Pavithra switches to the screenshot deck
(exported Aug 10) without breaking sentence rhythm — rehearsed, not improvised.

## The five questions we most expect

1. **"You generated the fraud yourselves — didn't you just find what you
   planted?"** (Vijayalakshmi) — Layered answer: honest economy tuned first;
   emergent fraud from incentive parameters, not labels; thresholds
   calibrated on honest actors only; held-out scenarios hash-committed after
   the spec freeze, evaluated once, misses reported. Then the claim, per the
   recorded OQ #12 attestation — **delete the inapplicable branch once
   DECISIONS records the outcome**:
   - *Branch A (attestation succeeded):* the held-out scenarios were
     authored by a team member who had **not read the detection spec** —
     enforced from 29 July, verifiable through HELDOUT_COMMITMENT hashes and
     commit dates — so they test detection of independently-conceived fraud,
     not pattern-matching on our own plants.
   - *Branch B (attestation failed):* the held-out test measures robustness
     to unseen parameterizations and structures of known typologies — the
     scenario author had access to the spec, and we say so rather than
     claim an independence we can't prove.
   Then the limits, unprompted, in either branch: synthetic ≠ real-world
   generalization; one team, shared schema; good-faith firewall, not an
   independent red team.
2. **"Why not machine learning?"** (Mary Vivitha) — No labeled real-world
   training data exists for this domain, and supervised models on synthetic
   labels would launder our assumptions into "AI." Structural rules are
   explainable to an investigator and a court. GDS algorithms *are* the
   ML-adjacent part (unsupervised community/centrality); an embedding-based
   anomaly layer is honest future work once real data exists.
3. **"What happens at real-world scale / 10M nodes?"** (Poonkundran) —
   Indexes and targeted queries hold; exact betweenness gets sampled; batch
   windows; Community→Enterprise for RBAC and clustering. Numbers from
   DATA_MODEL design notes.
4. **"Where would the real data come from? Who shares it?"** (Don Gabriel) —
   The honest answer: the technology is the easy half. TPAs and reinsurers
   already see multi-insurer flows (that's the wedge); an accreditor
   consortium is the second path; privacy law means hashed identifiers and
   consent frameworks — which our shared-endpoint signals survive better
   than content-based ones do.
5. **"What did you *not* detect? What are your false positives?"** (Mary,
   then Pavithra for the FP-dismissal demo beat) — Read the actual held-out
   misses from the Aug 9 evaluation; per-typology FP modes from
   DETECTION_SPEC; the live dismissal in the demo already showed we triage
   our own noise.

## Rehearsal log

| date | run | time | notes |
|---|---|---|---|
| _Aug 10_ | dress | | |
| _Aug 11_ | 1–3 | | |
