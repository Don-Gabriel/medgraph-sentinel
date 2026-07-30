# Day 2 Playbook — Surprise Constraint Sprint, Solo (Aug 13)

Rewritten 2026-07-30 (ADR-027) for **one implementer**. No rubric was
published (ADR-013), so we prepare *shapes*, not guesses. The architecture
was designed so each shape lands on a prepared seam.

**What changes when you're alone:** a team parallelises a surprise; one
person cannot. There is no scribe, no reviewer, no second pair of eyes on a
rabbit hole, and nobody building the demo slice while you build the data
slice. The solo compensations are: (1) a written protocol followed
mechanically, (2) everything rehearsable rehearsed **before** Aug 13, and
(3) hard timers replacing the missing teammate who would have said "stop."

## Solo sprint protocol (first 20 minutes, whatever the constraint)

1. **10 minutes, laptop closed.** Write the constraint in my own words on
   paper. Match it against the three shapes below. Pick ONE seam. Decide
   what the *demoable end state* is — the thing shown on screen at the end
   — before deciding any implementation step.
2. **5 minutes:** write the plan as an ADR stub in DECISIONS.md and commit
   it immediately (judges reading live decision logs is a work-sample
   moment — solo, the ADR also replaces the team huddle as the thing that
   stops scope drift).
3. **5 minutes:** write 3–5 checkpoint tasks with timestamps next to them
   (e.g. "13:30 — schema + generator emitting; 14:30 — loaded + query
   returns; 15:15 — alert visible in console"). These are the timers.
4. **Standing rules for the day:**
   - The demo stack stays UP all day. Develop against a *second* data dir /
     dev containers; `main` and the running demo are never broken.
   - Commit every 30–45 minutes, whatever state. Push every commit — the
     laptop is still a single point of failure.
   - **Half-time rule:** at the midpoint of the sprint window, cut to
     whatever demos end-to-end. A narrow working slice beats a wide broken
     one — and solo, there is no one to finish the second slice anyway.
   - **20-minute stuck rule:** stuck twice on the same error → that
     sub-task is cut or stubbed, immediately. This replaces the teammate
     who would have pulled me out of the hole.

## Shape A — new node or edge type
*(e.g. "add Accreditor organisations", "model hospital ownership chains")*

Prepared seam: schema + generator + loader are contract-driven; a new
`rel_*.csv`/node file is one registration line for the loader; the console
needs nothing (data-driven styling, ADR-008).

Sequence (solo = strictly this order, no parallel tracks):

1. DATA_MODEL.md table rows (5 min — the doc is the design surface).
2. `graph/schema.cypher`: constraint + any index.
3. Generator: population block in config + emitter.
4. Regenerate to the dev data dir (same seed), load into dev DB.
5. **Payoff move:** one new registry rule (YAML + Cypher) that consumes the
   new type and emits alerts — a new node type that changes an alert is a
   demo; one that just exists is trivia.

**Rehearsed, not improvised:** the full drill ("add `Accreditor` +
`ACCREDITED_BY` + a rule flagging clinics whose accreditor was sanctioned")
is executed end-to-end ONCE before event day (Aug 10, timed — target
90 min solo). The measured time is the Day-2 pacing baseline; the drill
also leaves muscle memory of the exact five files that change.

## Shape B — external API integration
*(e.g. "check doctors against a sanctions-list API", "send alerts to a webhook")*

Prepared seam: the narration module's cache-or-fallback pattern IS the
integration pattern — fetch → normalize → disk cache → deterministic
fallback when offline (venue wifi is still not trusted on Day 2).

1. New `api/integrations/<name>.py` adapter copying the narration module's
   shape (that file is the template — know it cold).
2. Surface where it changes something visible: a property on entities, a
   score modifier, a new evidence-panel field.
3. No credentials / no reachable service → stub the client behind the same
   adapter interface, demo with the fallback, and *say so* — the pattern is
   the deliverable.

**Rehearsed, not improvised:** I can sketch the adapter skeleton from
memory (fetch/normalize/cache/fallback, ≤ 40 lines). Rehearsal = write it
once against a fake local endpoint during the Aug 10 drill window if time
allows; otherwise the narration builder walkthrough during rehearsal round
2 covers the pattern.

## Shape C — stress test / scale
*(e.g. "load 500k nodes", "how fast at 10×?")*

Prepared seam: the generator scales by config; determinism makes runs
comparable; the centrality scaling story is already measured and written
as a jury answer (ADR-028).

1. Scale knobs: population counts in `generator/config.yaml` ×10; demo
   machine already runs the 16 GB profile.
2. Regenerate to a **separate** data dir — never overwrite the committed
   demo dataset on event day; load with LOAD CSV (ADR-025 numbers already
   known).
3. Measure honestly: load time, per-rule detection time, subgraph latency.
   Deliver as a small table + the "what breaks at 10M" narrative
   (DATA_MODEL notes + ADR-028) — judges reward measured limits.
4. Known risks at 10×: centrality (ADR-028 already ships the answer:
   degree/PageRank scale, exact betweenness doesn't — sampled or skipped,
   and say why), Louvain memory (ADR-026 numbers), LOAD CSV batching.

**Rehearsed, not improvised:** the ×10 generate/load/detect run happens
ONCE before event day (Aug 11 drill #2, timed) so the numbers are known
*before* they ask. If drill #2 gets cut (MILESTONES ladder rung 7), the
fallback is the 51k-node measured numbers plus the ADR-028 extrapolation —
still a real answer, and honest about being an extrapolation.

## If it's none of the three shapes

Run the protocol anyway — paper restatement, ADR stub, checkpointed tasks,
half-time cut. Any constraint decomposes into data (Shape A thinking),
service (Shape B thinking), or load (Shape C thinking) parts. The rehearsed
muscle is the deliverable; the shapes are just where it was built.

## Drill cards — turnkey (open, start timer, go)

Each card is self-contained: constraint, timer, exact files, success
criterion. No setup thinking required — the setup IS step 0 of the card.
Run drills against a scratch data dir + throwaway container so the demo
stack stays untouched (the pattern below is proven — it ran the
calibration, the freeze re-evaluation and the held-out one-shot).

**Shared step 0 (every drill):** open a terminal in the repo root, then:

```
docker run -d --name mg-drill -p 7991:7687 -e NEO4J_AUTH=neo4j/drill_pw -e NEO4J_server_memory_heap_initial__size=2G -e NEO4J_server_memory_heap_max__size=2G -e NEO4J_server_memory_pagecache_size=1G -e NEO4J_dbms_security_procedures_unrestricted="gds.*" -v "%TEMP%\mg_drill_import:/var/lib/neo4j/import" medgraph-neo4j:demo
```

Env for every python command in a drill:
`NEO4J_URI=bolt://localhost:7991  NEO4J_PASSWORD=drill_pw`.
Teardown when done: `docker rm -f mg-drill`.

---

### DRILL A — new node type + rule (Shape A) · timer: 90 min

**Constraint (read verbatim, start timer):** "Add Accreditor
organisations. Clinics are ACCREDITED_BY an Accreditor; some accreditors
have been sanctioned. Flag clinics whose accreditor was sanctioned."

Files, in strict order (this IS the rehearsed path):
1. `docs/DATA_MODEL.md` — add the `Accreditor` node table
   (id `ACR_` prefix, name, sanctioned: bool) + `ACCREDITED_BY`
   (Clinic)→(Accreditor) row. ~5 min.
2. `graph/schema.cypher` — one uniqueness constraint line. ~2 min.
3. `generator/config.py` — config model block; `generator/config.yaml` —
   population (e.g. 12 accreditors, 2 sanctioned, 70% of accredited
   clinics linked); `generator/economy.py` — emit in `build_static`;
   `generator/writer.py` — register `accreditors.csv` +
   `rel_accredited_by.csv`. ~25 min.
4. `loader/load.py` — one line each in `NODES` and `RELS`, prefix `ACR_`
   into `PREFIX_LABEL`. ~5 min.
5. Regenerate to scratch + load into mg-drill:
   `python -m generator --seed 42 --out %TEMP%\mg_drill_data` then copy
   csv → `%TEMP%\mg_drill_import`, then
   `DATA_DIR=%TEMP%\mg_drill_data python -m loader`. ~10 min.
6. **Payoff:** `detection/rules/sanctioned_accreditor.yaml`
   (kind: cypher) + `detection/rules/impl/sanctioned_accreditor.cypher` —
   match (c:Clinic)-[:ACCREDITED_BY]->(a:Accreditor {sanctioned:true}),
   count claims, score by volume ramp. Run
   `python -m detection.run --rules sanctioned_accreditor`. ~25 min.
7. Success = alert visible via the API/console pointed at mg-drill, and
   the closing ADR paragraph committed. Buffer: ~15 min.

**Rehearse aloud:** why the console needs zero changes (self-describing
alerts, ADR-008) — that sentence is the payoff of the whole drill.

### DRILL B — external service adapter (Shape B) · timer: 60 min

**Constraint:** "Check doctors against a sanctions-list API and surface
it on entities."

1. `api/integrations/__init__.py` + `api/integrations/sanctions.py`
   copying the narration shape: fetch → normalize → disk cache
   (`api/integrations_cache/`) → deterministic fallback (empty list +
   `source: fallback`) when offline. Stub client returns 2–3 fictional
   hits keyed by doctor id. ~30 min.
2. Surface: `GET /api/v1/entities/{id}` gains a `sanctions` field (one
   line in `api/entities.py`). ~10 min.
3. Success = entity endpoint shows the field with `source` honestly
   labeled; say the pattern sentence: "same cache-or-fallback contract as
   narration — the venue never depends on someone else's uptime." ~5 min
   + buffer.

### DRILL C — ×10 scale test (Shape C) · timer: 90 min

**Constraint:** "How does it behave at 10×?"

1. Copy `generator/config.yaml` → `%TEMP%\big.yaml`; multiply
   `patients`, `claims`-driving counts ×10 (leave fraud rates alone). ~10 min.
2. `python -m generator --seed 42 --config %TEMP%\big.yaml --out
   %TEMP%\mg_big` (~2 min measured at 1×; expect ~1–2 min at 10×). Copy
   csv → import mount; `DATA_DIR=%TEMP%\mg_big python -m loader` —
   record load time (15 s at 1×; LOAD CSV batching is the watch item).
3. `python -m detection.run` against mg-drill — record per-rule seconds
   (3–9 s at 1×; all rules are index-backed 1–2 hop queries + one
   Louvain, so expect roughly linear).
4. Deliver as a table + the ADR-028 sentence: exact betweenness would be
   hours here, which is why no shipped rule uses it; sampled betweenness
   (2048) is the documented fallback.
5. Success = three measured numbers (generate / load / detect) written
   into the live ADR before the timer ends.

## What is explicitly NOT attempted solo on Day 2

- Parallel tracks of any kind — one seam, one sequence, one demoable slice.
- Frontend feature work — the console is typology-agnostic by design; if a
  constraint seems to demand console changes, the answer is a new alert
  type surfacing through the existing UI, and saying so is the
  architecture flex.
- Live debugging of the demo stack — it stays up, untouched, all day.
- Heroics in the last 30 minutes. Final half hour = commit, push, write
  the closing ADR note, prepare the two-minute walkthrough of what shipped.
