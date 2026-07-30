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
> offer is provable ordering, in git. On July 30th, before a single
> detection query existed in this repository, I wrote five held-out fraud
> scenarios, stored them outside the repo, and committed their SHA-256
> hashes — that commit is in the history. The rules were written
> afterwards and calibrated only on the honest economy. Then I committed a
> pre-registration — no rule, threshold, or generator setting changes based
> on the results, misses get reported as they land — pushed it, and only
> then injected the sealed scenarios and ran the rules exactly once. So
> the history proves the test set wasn't written to match the rules, and
> the pre-registration proves the rules weren't tuned to pass the test.
> What it cannot prove is that one brain didn't unconsciously author
> detectable scenarios — it's a discipline claim, not an independence
> claim. Here are the results, including the two misses, which I'll
> explain rather than excuse."

## Held-out results (2026-07-30 one-shot — real numbers, show the slide)

**8 expected typology legs across 5 scenarios: 5 detected, 2 missed, 1
detected-at-reduced-severity.** Every scenario produced at least one alert
on its entities; the dev-world's 81 alerts re-fired byte-stably (97 total −
16 scenario-touching = exactly 81), proving injection perturbed nothing.

| scenario (what it tests) | expected | result |
|---|---|---|
| S1 ghost with institutional veneer (accredited, 25 beds, two feeders) | ghost_clinic | **caught, low 42.7** — the veneer suppressed the footprint feature exactly as probed; plus kickback + credential cross-hits on its brokers |
| S2 cross-jurisdiction licence share + revoked biller holding a second valid credential | credential_laundering | **MISSED** (prepared answer #1 below) |
| S3 low-and-slow kickback (12% stake, honest-band commissions, small regular shell transfers) | kickback_ring | **caught, medium 54.6** on the primary pair, low on the second; its clinics also drew ghost mediums |
| S4 same-window identity reuse across two countries, device-clean, different brokers | impossible_travel | **caught, low 42.0** — the date collision fired; severity stayed low because the scenario deliberately removed every escalation signal |
| S5 composite, every leg sub-threshold by design | all four | **ghost medium + kickback low caught; credential and travel legs missed as engineered** (prepared answers #1, #2) |

## The two misses — prepared answers (deliver with confidence, not apology)

**Miss #1 — credential laundering across jurisdictions (S2, S5).** "The
rule carries two false-positive guards, each individually justified by the
honest data: shared licence numbers only count within one issuing body or
country, because honest number collisions never span them; and
post-revocation billing is suppressed when the doctor holds another valid
credential, because 27 honest rostered doctors would otherwise fire daily.
My held-out author abused exactly that: a licence cloned *across*
jurisdictions, held by a doctor who kept one valid credential. Each guard
is right; their composition is a blind spot. The fix is a scored
OR-composition instead of hard guards — it's specified as next-build, and
per my pre-registration I did not patch it after seeing the result. I'd
rather show you a blind spot I can explain than a benchmark I tuned."

**Miss #2 — feasible-window identity reuse (S5's travel leg).** "The
travel rule flags only what is physically impossible under a whole-day
matrix — same-day treatment in two countries. S5's identities moved on
two-to-three-week gaps: suspicious, but possible, and the rule refuses to
call possible things impossible. That conservatism is why it produced zero
medium-or-high false positives on ten thousand honest patients. Catching
feasible-but-suspicious reuse belongs to a frequency signal — reuse count
across insurers — which is the typology's second axis, listed as
next-build."

## Demo click path (FINAL — validated against the real console 2026-07-30)

**Ordering decision (from the projector review):** lead with
`impossible_travel`, not `ghost_clinic`. The travel alert renders 19 nodes
— two ember-haloed identities, two conflicting claims, two countries — and
reads instantly from three metres. The ghost alert renders 117 nodes and
needs narration to decode. Open with the one that lands in a glance, then
go deep on the one that shows analytical depth. Screenshot deck beats are
numbered in the OLD order; the deck is the fallback, not the script.

1. Console open pre-loaded (never boot live). Header: 52,071 nodes,
   199,349 relationships, 81 alerts, health `ok`. *One breath on synthetic
   data: "fictional entities, real corridor economics, no real patient
   data anywhere."*
2. Alert queue: point at the severity zone — the hot band at the top is
   colour-coded, and the typology chips are simultaneously the counts and
   the filters. "Eighty-one alerts, and an investigator starts at the top."
3. **Open ALT_000068 — impossible travel.** Let the graph land before
   speaking. "One passport. Two patient identities. Two countries. Same
   day. One person cannot be on two operating tables in two countries on
   the same date — that is not a probability, it is a physical
   impossibility." Point at the two haloed nodes.
4. Narration panel: read one sentence aloud, then say what it is —
   "pre-generated at build time, committed to the repo, no API call at
   demo time. Offline by construction."
5. Mark it `reviewed` with a note — the investigator workflow beat, two
   seconds.
6. **Back to queue, clear the filter, open ALT_000062 — ghost clinic.**
   This is the depth beat: "Fifty-six claims. Zero beds. One doctor. One
   broker feeding ninety-five percent of them. One account taking every
   payout. Every patient visited exactly once and never appears again."
   Then the line the whole project is built on: *"Every one of those
   claims looks fine on its own. The fraud is only visible in what they
   share."*
7. Point at the evidence panel's opening sentence — "5 of 6 ghost-clinic
   indicators fired strongly" — and say that a rule that cannot explain
   itself is useless to an investigator.
8. Optional if time (≥ 45 s left): dismiss a documented low-severity false
   positive live — FP awareness beats a seventh feature.

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
