# Pitch — 10 Minutes, Day 1 (Aug 12)

Version 2 (solo — ADR-027). One presenter: J Don Gabriel, start to finish.
Revise after the Aug 7 demo build when the real click path exists; final
version locks Aug 11 after rehearsal ×3. Timings are hard budgets — the
timer runs at every rehearsal. Solo delivery notes: no handoffs to cover a
breath, so beats end on written sentences, not improvisation; the demo is
driven and narrated by the same person, which the click path below is paced
for (fewer clicks, more pointing).

## Minute-by-minute

| time | beat | content |
|---|---|---|
| 0:00–1:00 | Hook | One patient journey, five record-keepers, nobody sees the chain. "Every record looks fine. The fraud is only visible in the relationships." One sentence on what I built. |
| 1:00–2:00 | The insight | Per-claim detection catches bad claims, never bad *networks*; organised fraud is always a network. Fraud-is-relational ⇒ graph database. Name the four shipping typologies in one breath; "two more are specified and waiting" (ADR-024 — roadmap, said with confidence, not apology). |
| 2:00–2:45 | What I built | 30-second architecture: synthetic economy → Neo4j graph (50k nodes) → detection layer → investigator console. "docker compose up, three minutes, everything you're about to see runs offline on this laptop." |
| 2:45–6:15 | **Live demo** | The click path below, driven and narrated solo — rehearsed as one continuous monologue. |
| 6:15–7:45 | How I know it works | The circularity defense as a *feature*: honest economy first, emergent fraud from incentives, thresholds calibrated on honest actors only — then the held-out claim, verbatim from DATA_GENERATION §5 (reproduced below). Show the precision/recall slide **including misses**. State the limits unprompted. |
| 7:45–8:45 | Architecture & honest limits | Stack choices in three sentences (why Neo4j, why batch alerts, why one LLM call). What production needs that this doesn't: consortium data sharing, entity resolution, RBAC. "I know where the prototype ends." |
| 8:45–10:00 | Who buys it + close | Insurers/TPAs/accreditors/health authorities; the wedge is the TPA. Close honestly on the build: one person, thirteen days, every line explainable because I wrote every line — ask me about any module. Invite questions. |

## The held-out claim — exact wording (do not improvise, do not strengthen)

> "I built this alone, so I can't offer you author independence — the same
> person wrote the fraud scenarios and the detection rules. What I can
> offer is provable ordering. On July 30th, before a single detection query
> existed in this repository, I wrote five held-out fraud scenarios, stored
> them outside the repo, and committed their SHA-256 hashes — you can read
> that commit in the history. The rules were written afterwards, calibrated
> only on the honest economy, frozen on August 6th, and run against those
> scenarios exactly once, on August 9th. So the history proves the test set
> wasn't written to match the rules and the rules weren't tuned against the
> test set. What it cannot prove is that one brain didn't unconsciously
> author detectable scenarios — it's a discipline claim, not an
> independence claim. Here are the results, including what we missed."

## Demo click path (draft — finalize against the real dataset Aug 7)

1. Console open pre-loaded (never boot live). Header stats: ~50k nodes,
   ~190k relationships, alert counts by typology. *One breath on synthetic
   data: "fictional entities, real corridor economics."*
2. Alert queue sorted by score. Point at the spread of typologies. Filter to
   `ghost_clinic`, open the top alert.
3. Evidence subgraph: the clinic, its feeder broker(s), the payout account
   hub, the claim fan. Narrate the structure ("every one of these claims
   looks fine alone — watch what they share").
4. Narration panel: the plain-English explanation. Say it's a cached Claude
   call with an offline fallback — honesty beats magic.
5. Mark the alert `reviewed` with a note — the investigator workflow beat.
6. Second alert, different family: `impossible_travel` — one identity on two
   operating tables in two countries days apart (structural, not
   statistical — the contrast with alert #1 shows range, and it lands in
   one sentence).
7. Back to queue; point at an alert to *dismiss* live as a documented
   false positive (standardized dental package) — showing FP awareness is
   worth more than a seventh feature.

Fallback path: if anything hangs, switch to the screenshot deck (exported
Aug 10) without breaking sentence rhythm — solo, this must be a rehearsed
single keystroke (deck open on a second desktop), not a window hunt.

## The five questions I most expect

1. **"You generated the fraud yourself — didn't you just find what you
   planted?"** — Layered answer: honest economy tuned first; emergent fraud
   from incentive parameters, not labels; thresholds calibrated on honest
   actors only; then the held-out claim, verbatim from the block above —
   ordering, not independence, and say so before they do. Limits stated
   unprompted: synthetic ≠ real world; one author; a discipline claim.
2. **"Why not machine learning?"** — No labeled real-world training data
   exists for this domain, and supervised models on synthetic labels would
   launder my assumptions into "AI." Structural rules are explainable to an
   investigator and a court. GDS algorithms *are* the ML-adjacent part
   (unsupervised community/centrality); an embedding-based anomaly layer is
   honest future work once real data exists.
3. **"What happens at real-world scale / 10M nodes?"** — Indexes and
   targeted queries hold; centrality is the pressure point and the
   architecture already treats it that way (measured numbers + the ADR-028
   answer); batch windows; Community→Enterprise for RBAC and clustering.
4. **"Where would the real data come from? Who shares it?"** — The honest
   answer: the technology is the easy half. TPAs and reinsurers already see
   multi-insurer flows (that's the wedge); an accreditor consortium is the
   second path; privacy law means hashed identifiers and consent
   frameworks — which shared-endpoint signals survive better than
   content-based ones do.
5. **"What did you *not* detect? What are your false positives?"** — Read
   the actual held-out misses from the Aug 9 evaluation; per-typology FP
   modes from DETECTION_SPEC; the live dismissal in the demo already showed
   I triage my own noise.

## Rehearsal log

| date | run | time | notes |
|---|---|---|---|
| _Aug 10_ | dress | | |
| _Aug 11_ | 1–3 | | |
