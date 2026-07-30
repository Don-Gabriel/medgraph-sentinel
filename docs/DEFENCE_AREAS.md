# Defence Areas — Jury Q&A Assignments

**This is not module ownership — and as of the 2026-07-30 re-plan
(ADR-024), it is explicitly not authorship either.** One person
(J Don Gabriel) is writing nearly all the code on the one shared laptop.
**Four of us will defend code we did not write.** That is normal in real
engineering teams and the jury may probe exactly this; the defence is
genuine understanding, rehearsed aloud — never pretended authorship. If
asked "did you write this?", the answer is the honest one: "Don drove the
implementation; this area is mine to know, and I can walk you through it."

## Deliverables each person owns in git (ADR-024 reassignment)

Everyone commits **their own work under their own git identity** from the
shared laptop (CONTRIBUTING "Shared-machine identity") in daily laptop
slots (MILESTONES). This is real work product, not decoration:

| person | owns and commits |
|---|---|
| J Don Gabriel | nearly all implementation (generator, loader, detection, api, frontend, ops) |
| Pavithra R | held-out scenarios (off-repo until Aug 9 — ADR-016), demo rehearsal + demo driving, README/PITCH screenshots + screenshot fallback deck |
| Vijayalakshmi G | PITCH.md (v2 with real click path, claim branch), GLOSSARY.md |
| Mary Vivitha M | DEMO_RUNBOOK.md upkeep, **cold-start test execution** (ADR-019, Aug 10) and its recorded results |
| Poonkundran R | DAY2_PLAYBOOK.md upkeep, **fresh-clone verification** (Aug 8, clean Docker state) and its recorded results |

## Defending code you did not write

Per area: what must be explainable **cold — out loud, no notes, no
laptop — regardless of who typed it**. Rehearsal protocol (MILESTONES):
**round 1 Aug 9 evening** (each person teaches their area to the room; every
stumble is a doc fix that same evening), **round 2 Aug 10** after the dress
rehearsal, **question roulette Aug 11** (any question below, any person,
timed). A person who cannot explain an item aloud by Aug 10 does not get
that question deflected to Don on Day 1 — they get more rehearsal.

---

## Vijayalakshmi G — data generation & the synthetic economy

Primary docs: DATA_GENERATION.md, generator config. Also owns: PITCH.md,
GLOSSARY.md.

**Must be explainable regardless of authorship:**
- The layered fraud design: honest economy → emergent (incentive
  parameters) → planted cells → held-out overlays; where ground truth comes
  from and why no `is_fraud` flag exists anywhere.
- Why thresholds are calibrated on the honest economy only (circularity
  defense), and the honest limits of the whole protocol.
- Determinism: seed 42, byte-identical regeneration, why the dataset is
  committed (ADR-005/006).
- What the population table says and why it was corrected (ADR-021).
- Why `narrative_fingerprint` still ships although typology 4 is descoped
  (ADR-024: substrate for next-build; one sentence).

1. *"Didn't you just detect the fraud you planted?"* — the layered answer,
   ending with the claim branch OQ #12 resolved to, limits stated unprompted.
2. *"How do you know your synthetic economy is realistic?"* — gravity-model
   corridors, Zipf sizes, lognormal pricing, honest noise containing weak
   versions of every fraud signal.
3. *"Why is the dataset committed instead of generated fresh?"* — ADR-005/006.
4. *"What does 'emergent' fraud actually mean here?"* — incentive parameters
   on actors; fraud from decision rules; ground truth derived, never written
   into the data.
5. *"How would this work with real data?"* — it wouldn't directly: entity
   resolution, consortium sharing, privacy law; the generator exists because
   real data is unobtainable.

## Poonkundran R — graph schema, Cypher, and why Neo4j

Primary docs: DATA_MODEL.md, graph/schema.cypher, loader. Also owns:
DAY2_PLAYBOOK.md, fresh-clone verification.

**Must be explainable regardless of authorship:**
- The claim-centric star, drawn from memory on a whiteboard.
- Every constraint and index, each mapped to the named query that needs it —
  and why passport/licence are deliberately NOT unique.
- The loader contract end-to-end: wait for Bolt → schema → wipe → load →
  manifest validation → fail loudly; wipe-and-load vs incremental, and why.
- The OQ #1 benchmark result: LOAD CSV vs neo4j-admin import numbers, which
  won and why (ADR-025).
- What breaks at 10M nodes (DATA_MODEL design notes).

1. *"Why Neo4j over PostgreSQL?"* — relational-not-transactional fraud;
   traversals + community detection vs recursive CTEs; ADR-001.
2. *"Why these constraints and indexes?"* — each maps to a named query.
3. *"What breaks at 10 million nodes?"* — sampled betweenness, batch windows,
   Community Edition limits bite first.
4. *"Walk me through the model for one claim."* — the star, from memory.
5. *"How does data get in, and how fast?"* — loader contract + the measured
   load time and benchmark numbers (ADR-025).

## Mary Vivitha M — detection typologies & graph algorithms

Primary docs: DETECTION_SPEC.md, detection rules. Also owns:
DEMO_RUNBOOK.md, cold-start test execution.

**Must be explainable regardless of authorship:**
- All four shipping typologies: behaviour → signature → features → score,
  each in under two minutes; ghost clinic in full depth.
- The descope story as an asset: which two were cut, why those two, and
  that they remain fully specified as next-build (ADR-024) — say it
  before the jury finds it.
- What Louvain, PageRank, and betweenness each contribute, in plain words.
- Every rule's documented FP modes and the multi-feature score mitigation.
- The rule registry: why a seventh typology is YAML + a query, no API or
  frontend change (this doubles as the Day-2 answer).

1. *"Explain one typology end to end."* — ghost clinic by default; be ready
   to switch to any of the four.
2. *"Why Louvain? What does betweenness give you that degree doesn't?"* —
   communities without labels; brokers bridging communities; PageRank ranks
   referral influence.
3. *"What's your false-positive story?"* — documented FP modes per rule,
   thresholds calibrated on honest actors.
4. *"Why only four typologies?"* — capacity honesty: cut ladder pre-agreed
   (ADR-017), executed under the one-laptop constraint (ADR-024); two more
   are fully specified with FP modes — that's the roadmap, not a gap.
5. *"How would you add a seventh typology right now?"* — registry entry +
   query; live answer on Day 2 if asked.

## J Don Gabriel — API design, narration, and deployment

Primary docs: INTERFACES.md §5–9, api/, docker-compose, DECISIONS.md.
Also: nearly all implementation (and first responder for any deep
implementation question another area cannot field).

**Must be explainable regardless of authorship:** (he wrote it — his burden
is breadth, plus backing up the other four without taking over their
answers.)

1. *"Walk me through the architecture."* — generator → committed CSVs →
   seed (load + detect) → Neo4j → FastAPI → console; the why of each arrow.
2. *"What exactly does the LLM do, and what happens offline?"* — one cached
   call per alert, committed cache, template fallback, 5 s timeout.
3. *"Why is the API read-mostly?"* — precomputed alerts; PATCH is the only
   write; demo safety + Day-2 lever.
4. *"How does a judge run this?"* — clone, .env, compose up, measured boot
   time; what's pinned and why.
5. *"What would production need?"* — auth/RBAC, consortium ingestion, entity
   resolution, incremental detection.

## Pavithra R — the investigator console & the demo itself

Primary docs: INTERFACES.md §6–7, frontend/, PITCH.md, DEMO_RUNBOOK.md.
Also owns: held-out scenarios (ADR-016 isolation until Aug 9), demo
rehearsal, screenshots + fallback deck.

**⛔ Until the held-out results are committed (Aug 9) she does not read
DETECTION_SPEC.md or `detection/` — her rehearsal of the demo click path
uses the console only, and her typology vocabulary comes from GLOSSARY.md,
which stays spec-safe.**

**Must be explainable regardless of authorship:**
- The demo click path from muscle memory, including every rehearsed
  recovery (RUNBOOK failure drills) and the screenshot-deck fallback.
- Why alert-then-drill-down, never the full graph (ADR-009); the 200-node
  server-side cap.
- How the console stays typology-agnostic (self-describing alerts,
  data-driven styling).
- The held-out protocol from the author's side: what she authored from,
  what she never saw, what the hashes prove, what the claim does NOT prove.

1. *"Why don't you show the whole graph?"* — investigators triage alerts,
   not hairballs; ADR-009; the cap.
2. *"Why Cytoscape.js?"* — small interactive subgraphs are its sweet spot;
   trade-offs per ADR-007.
3. *"What does an investigator actually do in this tool?"* — queue →
   evidence → narration → status/note; drive it from muscle memory.
4. *"How does the console handle a brand-new typology?"* — it doesn't need
   to know; alerts are self-describing.
5. *"You wrote the held-out scenarios — how, and why you?"* — authored
   off-repo from schema docs only, without reading the detection spec
   (ADR-016, OQ #12 attestation); hash-committed before evaluation; state
   the protocol's limits unprompted.
