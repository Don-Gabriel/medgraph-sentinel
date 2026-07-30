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

## What is explicitly NOT attempted solo on Day 2

- Parallel tracks of any kind — one seam, one sequence, one demoable slice.
- Frontend feature work — the console is typology-agnostic by design; if a
  constraint seems to demand console changes, the answer is a new alert
  type surfacing through the existing UI, and saying so is the
  architecture flex.
- Live debugging of the demo stack — it stays up, untouched, all day.
- Heroics in the last 30 minutes. Final half hour = commit, push, write
  the closing ADR note, prepare the two-minute walkthrough of what shipped.
