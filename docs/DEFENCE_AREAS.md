# Defence Areas — Jury Q&A Assignments

**This is not module ownership.** All five of us build everywhere (ADR-014).
This maps each person to the area they have read most deeply and **answer
first** when the jury asks about it. Anyone may add to an answer; the named
person opens.

> Assignment below is **provisional** (owner-proposed, [ASSUMED]). Confirm or
> reshuffle at the first team sync, then remove this notice.

Rule of preparation: each person must be able to answer their questions
**cold — out loud, without notes, without a laptop.** Practice answers on
each other during the Aug 11 rehearsals. If you can't answer one, that's a
gap in the docs — fix the doc, then learn it.

---

## Vijayalakshmi G — data generation & the synthetic economy

Primary docs: DATA_GENERATION.md, generator config.

1. *"Didn't you just detect the fraud you planted?"* — the layered answer:
   emergent vs planted vs held-out, thresholds tuned on the honest economy
   only, hash-committed held-out scenarios, and what the protocol does NOT
   prove (say the limits before they ask).
2. *"How do you know your synthetic economy is realistic?"* — gravity-model
   corridors, Zipf clinic/broker sizes, lognormal pricing, and honest noise:
   the honest world deliberately contains weak versions of every fraud signal.
3. *"Why is the dataset committed to git instead of generated fresh?"* —
   determinism, demo stability, 3-minute boot, byte-identical regeneration
   (seed 42), ADR-005/006.
4. *"What does 'emergent' fraud actually mean in your generator?"* — incentive
   parameters on actors, fraud arises from decision rules interacting; ground
   truth is derived from parameters, never written into the data.
5. *"How would this work with real data?"* — it wouldn't, directly: entity
   resolution, consortium data sharing, and privacy law are the real gaps;
   the generator exists precisely because real data is unobtainable.

## Poonkundran R — graph schema, Cypher, and why Neo4j

Primary docs: DATA_MODEL.md, graph/schema.cypher, loader.

1. *"Why Neo4j over PostgreSQL?"* — relational-not-transactional fraud;
   variable-length traversals and community detection vs recursive CTEs;
   ADR-001 alternatives.
2. *"Why these constraints and indexes?"* — every index maps to a named query
   (licence sharing, passport sharing, date windows, alert filters); and why
   passport/licence are deliberately NOT unique.
3. *"What breaks at 10 million nodes?"* — exact betweenness first (O(n·m) →
   sampled), then batch windows; Community Edition limits (single DB, no
   RBAC) bite before algorithms; DATA_MODEL design notes.
4. *"Walk me through the model for one claim."* — the claim-centric star,
   drawn from memory on a whiteboard: Claim → Patient/Clinic/Doctor/
   Procedure/Insurer/Broker/Account.
5. *"How does data get in, and how fast?"* — loader contract (wipe-and-load,
   manifest validation), LOAD CSV vs admin import benchmark result (OQ #1).

## Mary Vivitha M — detection typologies & graph algorithms

Primary docs: DETECTION_SPEC.md, detection rules.

1. *"Explain one typology end to end."* — pick ghost clinic: behaviour →
   signature → features → score; be ready to switch if they name another.
2. *"Why Louvain? What does betweenness give you that degree doesn't?"* —
   Louvain finds ring communities without labels; betweenness finds brokers
   *bridging* communities (hubs by position, not volume); PageRank ranks
   influence in the referral flow.
3. *"What's your false-positive story?"* — every rule has documented FP modes
   (exclusive-but-legitimate partnerships, standardized packages, refunds);
   multi-feature scoring; thresholds calibrated on honest actors.
4. *"How do you score and threshold?"* — raw features → 0–100 normalization,
   severity bands, calibration against honest-economy FP rates (OQ #4
   resolution).
5. *"How would you add a seventh typology right now?"* — registry entry +
   query, no API/frontend change; this doubles as the Day-2 answer.

## J Don Gabriel — API design, narration, and deployment

Primary docs: INTERFACES.md §5–9, api/, docker-compose, DECISIONS.md.

1. *"Walk me through the architecture."* — the one-breath version: generator
   → committed CSVs → seed (load + detect) → Neo4j → FastAPI → console;
   then the why of each arrow (ADR-005, ADR-008).
2. *"What exactly does the LLM do, and what happens offline?"* — one narration
   call per alert at build time, committed cache, template fallback, 5 s
   timeout on opportunistic live calls; why narration is the *only* LLM use.
3. *"Why is the API read-mostly? Where's the write path?"* — alerts are
   precomputed (demo safety, Day-2 lever); the only writes are investigator
   status/notes; PATCH contract.
4. *"How does a judge run this?"* — clone, `.env` from example, compose up,
   3 minutes post-pull; what's pinned and why (5.26 LTS + GDS 2.13, ADR-004).
5. *"What would production need that this doesn't have?"* — auth/RBAC
   (Enterprise), consortium ingestion, entity resolution, incremental
   detection instead of wipe-and-load; honest prototype/product line.

## Pavithra R — the investigator console & the demo itself

Primary docs: INTERFACES.md §6–7, frontend/, PITCH.md, DEMO_RUNBOOK.md.

1. *"Why don't you show the whole graph?"* — investigators triage alerts, not
   hairballs; alert-then-drill-down (ADR-009); the 200-node server-side cap.
2. *"Why Cytoscape.js?"* — interactive small-subgraph rendering is its sweet
   spot; sigma/D3 trade-offs (ADR-007).
3. *"What does an investigator actually do in this tool?"* — queue → evidence
   subgraph → narration → status/note; drive the demo path from muscle
   memory, including the rehearsed recovery if something breaks (RUNBOOK).
4. *"How does the console handle a brand-new typology?"* — it doesn't need
   to know: alerts are self-describing (typology key, title, implicated
   roles), styling is data-driven.
5. *"You wrote the held-out scenarios — how, and why you?"* — authored
   outside the repo from schema docs only, without reading the detection
   spec (isolation rule, ADR-016 — role confirmed via the OQ #12
   attestation); hash-committed before evaluation; state the protocol's
   limits unprompted (she is the person most fluent in its honest
   boundaries).
