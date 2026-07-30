# Jury Prep — Every Question, One Answerer

**Solo as of 2026-07-30 (ADR-027).** There is no deflection target: every
question lands on J Don Gabriel. This file is the drill sheet — each
question I must be able to answer **cold, out loud, no notes, no laptop**,
grouped by area, with the answer in compressed form or a pointer to where
the full answer lives. Rehearsal protocol at the bottom.

Format per question: **Q** → the answer skeleton (the 3–5 things that must
come out of my mouth) → pointer.

---

## Area 1 — The problem & the product

**Q: What does this actually do, in one minute?**
Cross-border medical tourism = five record-keepers, none sees the whole
chain; organised fraud engineers every record to look fine alone; the fraud
is only visible in relationships. We build the graph (patients, doctors,
clinics, brokers, claims, accounts, devices), run four typology rules +
GDS algorithms over it, and surface scored, explainable alerts in an
investigator console. → PROJECT_BRIEF.

**Q: Who buys this?**
Insurers/reinsurers (losing the money), TPAs (see cross-insurer flows —
the wedge), accreditation bodies, national health authorities. →
PROJECT_BRIEF "Who would buy this".

**Q: Where would real data come from?**
Honest answer: the technology is the easy half. TPAs and reinsurers already
aggregate multi-insurer flows; accreditor consortium second; privacy law
forces hashed identifiers — shared-endpoint signals survive hashing better
than content-based signals. → PITCH Q4.

**Q: Why is nobody doing this already?**
Per-claim scoring is the incumbent; cross-org graph needs data sharing
(legal, not technical, blocker) — which is why the prototype is synthetic
and says so.

## Area 2 — Data generation & the synthetic economy

**Q: Didn't you just find what you planted?** *(the big one)*
Layered: (1) honest economy simulated first, tuned to look right with weak
versions of every fraud signal; (2) emergent fraud = incentive parameters
on ~5% of actors, fraud emerges from decision rules — ground truth derived,
never labeled; (3) thresholds calibrated on honest actors only; (4)
held-out scenarios: hash-committed 2026-07-30 **before any detection query
existed**, evaluated once against frozen rules. Then the exact claim
wording — ordering, not independence — verbatim from DATA_GENERATION §5.
Never stronger.

**Q: How do you know the synthetic economy is realistic?**
Gravity-model corridors over real countries/cost levels, Zipf clinic/broker
sizes, lognormal pricing, 1–3 claims per journey, honest noise mandatory:
family device sharing, shared registered offices, declared broker stakes,
~3% honest revocations. Limits stated: it's plausible, not validated
against real claim distributions — real data is unobtainable, which is the
market gap itself. → DATA_GENERATION §2.

**Q: What does "emergent" mean here, concretely?**
`overbilling_propensity`, `steering_greed`, `identity_recycling`,
`shell_layering` — parameters, not labels; e.g. a greedy broker meets a
paying clinic and a kickback ring *emerges*. `actor_params.csv` records
parameters; an evaluation script derives affected entities; detection code
has no path to that directory. → DATA_GENERATION §3.

**Q: Why is the dataset committed rather than generated at boot?**
Determinism (same graph every clone, demo script can name entities), boot
time (3-minute budget is load time), demo stability, and the held-out story
(evaluation regenerates separately). → ADR-005/006.

**Q: Seed and reproducibility?**
One `numpy.random.Generator`, seed 42, config hash in the manifest, no
timestamps in artifacts; byte-identical regeneration is tested. → ADR-006/021.

## Area 3 — Graph schema & why Neo4j

**Q: Why Neo4j over PostgreSQL?**
The signals are traversals and community structure — multi-hop
variable-length paths and Louvain are what SQL is worst at; Cypher patterns
read aloud to a jury; GDS is the most mature algorithm library. Community
limits (single DB, no RBAC) named honestly. → ADR-001.

**Q: Walk me through the model for one claim.** *(whiteboard, from memory)*
Claim is the hub: FOR_PATIENT, AT_CLINIC, PERFORMED_BY, FOR_PROCEDURE,
BILLED_TO, ARRANGED_BY (commission), PAID_TO. Periphery: doctor HOLDS
credential ISSUED_IN country; clinic LOCATED_AT address IN_COUNTRY; broker
OPERATES_FROM; accounts OWNED_BY / TRANSFERRED; patient USED_DEVICE /
RESIDES_IN. Star keeps typology traversals 1–2 hops. → DATA_MODEL.

**Q: Why are passport and licence numbers NOT unique?**
A uniqueness constraint would make the fraud unrepresentable — shared
passports/licences ARE the typology 5/2 signals. Deliberate, indexed,
non-unique. → DATA_MODEL design notes.

**Q: Name an index and the query that needs it.**
`cred_license_no` → typology 2 licence-sharing lookup; `patient_passport`
→ typology 5; claim date indexes → typology 5 date windows + API;
alert_status/typology → console queue filters. Every index maps to a
shipping query (fingerprint index removed with the typology-4 descope). →
DATA_MODEL.

**Q: What breaks at 10M nodes?**
Indexes and targeted queries hold; exact betweenness O(n·m) does not — we
hit this at 51k nodes already (122 s) and re-architected: measured numbers
and the sampling/degree answer live in ADR-028. Batch feature extraction
moves to scheduled pipelines; Community Edition's single-DB/no-RBAC bites
before the algorithms do. → DATA_MODEL notes + ADR-028.

**Q: How does data get in, and how fast?**
Loader: wait for Bolt → schema DDL → wipe → LOAD CSV batched 5k rows/tx →
manifest count validation, fail loudly. Measured 15.3 s full load; admin
import measured 3.8 s but needs an offline DB — wrong architecture for a
seed service. → INTERFACES §4, ADR-025.

## Area 4 — Detection typologies & algorithms

**Q: Explain one typology end to end.** *(default: ghost clinic)*
Behaviour: paper clinic + cooperating broker bills for procedures never
performed. Signature: claim volume vs. tiny physical footprint, inflow
dominance (one feeder broker), payout concentration (one account), few
doctors, one-journey patients. Approach: Cypher feature extraction →
weighted 0–100 score; Louvain community as ring context. FP modes: honest
new day clinic with exclusive referral partner; single corporate account;
registered-office sharing — multi-feature score keeps single hits below
medium. → DETECTION_SPEC §1. *(Be ready to do the same for 2, 3, 5.)*

**Q: What do Louvain / PageRank / betweenness each buy you?**
Louvain: unsupervised communities — fraud cells are dense clusters of
broker+clinics+accounts; no labels needed. PageRank: influence ranking in
the referral flow. Betweenness: bridges between communities — but exact
betweenness is the scaling trap; ADR-028 records what we measured and what
we ship instead. Plain-words definitions in GLOSSARY.

**Q: What's your false-positive story?**
Every rule documents FP modes in the spec *before* implementation;
thresholds calibrated on the honest economy (FP-rate driven, not
label-recovery driven); the demo includes dismissing a documented FP live.
→ DETECTION_SPEC per-rule FP sections, DATA_GENERATION §6.

**Q: Why only four typologies?**
Capacity honesty: pre-agreed cut ladder (ADR-017), executed when capacity
collapsed (ADR-024→027). Typologies 4 and 6 stay fully specified with FP
modes — that's a roadmap with receipts, not a gap. Say it before they find it.

**Q: How would you add a seventh typology right now?**
Registry entry: YAML metadata + Cypher/Python impl; runner writes Alert
nodes + IMPLICATES edges; API and console need zero changes (alerts are
self-describing). This is the rehearsed Day-2 answer. → ADR-008.

**Q: Where does detection underperform? What did you miss?**
Read the dev-set numbers per typology and the held-out misses from the
evaluation — including which scenario legs no rule fired on. Numbers live
in DECISIONS (post-evaluation ADR) and the PITCH slide. Underperformance is
reported, not tuned away.

## Area 5 — API, narration & deployment

**Q: Walk me through the architecture.**
Generator (dev-time, seeded) → committed CSVs → compose `seed` loads a
graph that already contains precomputed alerts (ADR-018/029) → FastAPI
reads/updates alerts → React+Cytoscape console renders evidence subgraphs.
Detection runs on demand in development, never at compose-up. → INTERFACES.

**Q: What exactly does the LLM do, and what happens offline?**
One cached Claude call per top alert at build time; cache committed;
request time is cache → deterministic template fallback; live path off by
default, 5 s timeout. `/health` startup check makes a stale cache fail
loudly, never silently. → ADR-010/018.

**Q: Why is the API read-mostly?**
Alerts are precomputed batch output; PATCH status/note is the only write —
demo safety and investigator workflow; a new rule needs no API change. →
ADR-008.

**Q: How does a judge run this?**
Clone → `.env` (password + memory profile) → `docker compose up` →
console ≤ 3 min after images. GDS is baked into our own image at build time
because the stock plugin path downloads at container start — unusable
offline. → ADR-026, DEMO_RUNBOOK.

**Q: What would production need?**
Consortium data sharing + legal framework, entity resolution on messy
identifiers, Enterprise RBAC/clustering, incremental (streaming) detection
instead of batch, and real-data calibration. "I know where the prototype
ends." → PROJECT_BRIEF.

## Area 6 — Console & demo

**Q: Why don't you show the whole graph?**
50k nodes is noise; investigators triage a queue, then drill into a ≤ 300
node evidence subgraph (server-capped, trimmed by relevance; raised from
200 by owner decision 2026-07-30). → ADR-009, INTERFACES §6.

**Q: Why Cytoscape.js?**
Small interactive evidence subgraphs are its sweet spot; D3 is
lower-level for the same result; sigma targets huge graphs we deliberately
never render. → ADR-007.

**Q: What does an investigator do in this tool?**
Queue (filter by typology/severity/status) → alert → evidence subgraph +
implicated entities + summary numbers → narration → mark
reviewed/dismissed with a note. Drive it from muscle memory.

**Q: How does the console handle a brand-new typology?**
It doesn't need to know — alerts are self-describing (typology key, score,
summary_params, IMPLICATES roles); styling is data-driven.

## Area 7 — Process, protocol & the solo build

**Q: You built this alone? Really?**
Yes — originally a five-person plan; the team fell through (ADRs 024, 027
record the collapse honestly). The repo shows the replanning in public:
cut ladder executed, docs rewritten, every date held. One person, ~13 build
days, every module explainable because I wrote every line.

**Q: How much did AI write?**
AI-assisted throughout — disclosed in the README, per repo policy, not
per-commit. The bar that matters here: I can explain any line aloud,
unaided, and the hard rules forbid shipping anything I can't. Ask me about
any module — that's the test that counts.

**Q: What do the freezes protect?**
Detection freeze (Aug 6): rules can't chase the held-out set. Integration
freeze (Aug 8): demo stability; bug fixes and docs only. Dress rehearsal
(Aug 10): cold-start proof on the actual demo laptop. → MILESTONES.

**Q: Explain the held-out protocol and its limits.** *(know this cold)*
Authored five scenarios 2026-07-30 before any detection query existed;
stored off-repo; SHA-256 committed in a dedicated commit; not reopened
until the one-shot Aug 9 evaluation against rules frozen Aug 6. Proves
ordering (git history), NOT independence (one brain conceived both). The
exact pitch wording is in DATA_GENERATION §5 — deliver it verbatim, limits
unprompted.

**Q: Why no CI / why this branch workflow / why PRs solo?**
Small answers, honest: PRs batch reviewable diffs and mark milestones;
Conventional Commits keep the log scannable; CI decision recorded in
OPEN_QUESTIONS (#7) with its trade-off. The history is the work sample.

**Q: What's your single biggest technical risk and what did you do about it?**
Offline venue: images carried as a docker-save tarball with GDS baked in
(ADR-019/026), committed narration cache with loud staleness check
(ADR-018), screenshot deck + recording as rehearsed fallback modes
(DEMO_RUNBOOK). Second: exact betweenness at scale — measured, re-architected,
ADR-028.

---

## Rehearsal protocol (solo — this replaces four teammates asking me things)

- **Aug 9 evening — round 1:** answer every question above out loud,
  recorded on the phone, no notes. Listen back at 1.5×; every stumble
  becomes a doc fix or a re-drill card that same evening.
- **Aug 10 — round 2:** after the dress rehearsal, re-run only the cards
  that stumbled, plus all of Area 4 (detection is the most probed area).
- **Aug 11 — roulette:** shuffle this file's questions (any order, timer at
  90 s per answer), full pass. Anything still failing gets written onto a
  one-page crib that lives in the pitch notes — better an honest glance
  than a wrong answer.
- During the pitch Q&A there is no deflection and no "my teammate knows
  that" — the fallback for a genuinely unknown answer is the honest one:
  state what is known, state what isn't, point at where the repo documents
  it.
