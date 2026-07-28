# Day 2 Playbook — Surprise Constraint Sprint (Aug 13)

No rubric was published (ADR-013), so we prepare *shapes*, not guesses. The
architecture was designed so each shape lands on a prepared seam; the drills
below get rehearsed twice (Aug 10, Aug 11) with a timer.

## Sprint protocol (first 15 minutes, whatever the constraint)

1. **10-minute huddle, whole team, laptops closed.** Restate the constraint
   in our own words; check it against the three shapes below; pick the seam.
2. Write the plan as 4–6 claimable tasks in the group chat (CONTRIBUTING
   claim protocol — it exists for exactly this hour).
3. One person (rotating scribe) appends an ADR to DECISIONS.md *as we go* —
   judges watching us log decisions live is a work-sample moment.
4. Keep `main` green: branch per task, PRs small, demo from main only.
5. At half-time: cut scope to whatever demos end-to-end. A narrow working
   slice beats a wide broken one.

## Shape A — new node or edge type
*(e.g. "add Accreditor organisations", "model hospital ownership chains",
"add travel bookings")*

Prepared seam: schema + generator + loader are contract-driven.

1. DATA_MODEL.md: add the label/relationship table rows (5 min — the doc is
   the design surface).
2. `graph/schema.cypher`: constraint + any index.
3. Generator: new population block in config + emitter (the CSV conventions
   in INTERFACES §2 mean the loader picks up a new `rel_*.csv`/node file with
   one registration line).
4. Regenerate (same seed — additions don't disturb existing IDs), reload.
5. Payoff move: **wire it into one detection rule or one new registry rule**
   — a new node type that changes an alert is a demo; one that just exists
   is trivia. Console needs nothing (data-driven styling, ADR-014/ADR-008).

Rehearsal drill: "add an `Accreditor` node with `ACCREDITED_BY` edges and a
rule flagging clinics whose accreditor was sanctioned." Target: 90 minutes.

## Shape B — external API integration
*(e.g. "pull live FX rates", "check doctors against a sanctions-list API",
"send alerts to a webhook")*

Prepared seam: the API module boundary + the narration module's
cache-or-fallback pattern, which generalizes to any flaky external service.

1. New `api/integrations/<name>.py` adapter: fetch → normalize → cache to
   disk → deterministic fallback when offline (venue wifi is still not
   trusted on Day 2).
2. Surface it where it changes something visible: a property on entities, a
   modifier on scores, a new panel field.
3. If the required service needs credentials we don't have: stub the client
   behind the same adapter interface, demo with the fallback, and *say so* —
   the pattern is the deliverable.

Rehearsal drill: "enrich clinic countries with a live currency API, price
claims in local currency in the evidence panel." Target: 60 minutes.

## Shape C — stress test / scale
*(e.g. "load 500k nodes", "how fast are your queries at 10×", "run detection
under load")*

Prepared seam: the generator scales by config; determinism makes runs
comparable.

1. Scale knobs: population counts in `generator/config.yaml` ×10 (claims
   dominate — mind the 8 GB profile; switch the demo machine to the 16 GB
   profile).
2. Regenerate to a *separate* data dir (never overwrite the committed demo
   dataset on event day); load with the benchmark-chosen bulk path (OQ #1
   already measured both).
3. Measure honestly: load time, per-rule detection time, subgraph endpoint
   latency; deliver as a small table + the "what breaks at 10M" narrative
   (DATA_MODEL design notes) — judges reward measured limits over bravado.
4. Known risks at 10×: exact betweenness (switch that rule to sampled or
   skip it, and say why), Louvain memory (OQ #11 numbers), LOAD CSV
   transaction batching.

Rehearsal drill: 250k-node generate/load/detect run on the demo laptop with
timings recorded. Target: know our numbers *before* they ask. 90 minutes.

## If it's none of the three shapes

Run the sprint protocol anyway — the huddle, the task split, the live ADR.
The constraint will still decompose into data (Shape A thinking), service
(Shape B thinking), or load (Shape C thinking) parts. The rehearsed muscle
is the deliverable; the shapes are just where we built it.
