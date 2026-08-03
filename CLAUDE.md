# CLAUDE.md — project memory for MedGraph Sentinel

## Session start protocol (every session, in this order)

1. Read `docs/STATUS.md` — current state, blockers, next actions.
2. Read `docs/INTERFACES.md` — the contracts that prevent collisions.
3. Read only the docs your task needs:
   - **generator** → DATA_GENERATION, INTERFACES §2–3, DATA_MODEL
   - **detection** → DETECTION_SPEC, DATA_MODEL, INTERFACES §5
   - **API / narration** → INTERFACES §5–9, DATA_MODEL (Alert), DECISIONS ADR-010/018
   - **frontend** → INTERFACES §6–7, PITCH (click path)
   - **demo prep** → DEMO_RUNBOOK, MILESTONES, PITCH
   - **pitch / Q&A** → PITCH, PROJECT_BRIEF, DEFENCE_AREAS, GLOSSARY
4. Check `docs/OPEN_QUESTIONS.md` before assuming any answer.
5. Append significant choices to `docs/DECISIONS.md` as they happen.
6. Update `docs/STATUS.md` before ending — same commit as your work.
7. **⛔ HARD STOP — held-out discipline (ADR-027): the held-out scenario
   files live OUTSIDE the repo (path in the off-repo README; hashes in
   docs/HELDOUT_COMMITMENT.md). Do NOT open, paste, summarize, or commit
   them in any session before the one-shot evaluation (planned Aug 9). A
   session that has them in context while touching `detection/` destroys
   the temporal-separation claim's spirit even though the hashes hold.**

Read the rest of this file first in every session. The docs under `docs/`
are the design; this file is the standing context and rules.

## What this is

Fraud-intelligence graph over cross-border medical tourism: synthetic
economy → Neo4j graph → four shipping detection typologies (1, 2, 3, 5;
typologies 4 and 6 descoped per ADR-024, kept specified as next-build) →
investigator console.
Built **solo by J Don Gabriel** (ADR-027; originally planned as a 5-person
team) for the Hazzino Technologies State-Level Mega Hackathon (Theni,
Tamil Nadu):

- **Day 1 — Aug 12, 2026:** 10-minute pitch of a pre-built prototype to a
  technical jury and hiring recruiters; top 3–5 teams advance.
- **Day 2 — Aug 13, 2026:** live coding sprint with a surprise constraint.
- Venue network is assumed absent; the demo must run fully offline.
- This is a hiring drive: the repo, the commits, and the implementer's
  ability to explain any module aloud are the actual deliverables.
- Repo is private until the evening of Aug 11, then public.

## Stack (pinned — rationale in docs/DECISIONS.md)

- Neo4j **5.26 Community (LTS)** + GDS **2.13** (ADR-004), Cypher.
- Python **3.11**, FastAPI, Pydantic (ADR-003) for generator, loader,
  detection, API.
- React + Vite + Tailwind + Cytoscape.js (ADR-007).
- Narration: pre-generated committed data — all 81 texts written by a
  Claude assistant session and committed to `api/narration_cache/`, zero
  API calls anywhere, deterministic template fallback (ADR-032, supersedes
  ADR-010's live-call mechanism).
- Docker Compose: neo4j + one-shot seed (load, then detect) + api +
  frontend. Never generate data at boot (ADR-005).
- Out of scope, on purpose: Kubernetes, microservices, queues, cloud
  deployment, model training. At this size those signal poor judgement.

## Hard rules

1. **No code ships that a team member cannot explain aloud, unaided.** If a
   suggestion is clever but opaque, simplify it or document it until it's
   explainable. This outranks elegance and speed.
2. **Never invent a library, API, function signature, or Neo4j/GDS feature.**
   Verify against live documentation or mark explicitly for verification
   (pattern: OPEN_QUESTIONS entry + comment in code). GDS procedure
   signatures are always checked against the pinned 2.13 docs, never memory.
3. **Contracts before code.** Module seams are defined in
   docs/INTERFACES.md; changing a contract follows its change protocol
   (announce first, `contract:` PR prefix). Working *behind* a contract is
   free; changing one silently breaks four people.
4. **Append to docs/DECISIONS.md as decisions happen**, not at the end. It
   is the jury answer sheet.
5. **detection/, api/, frontend/ never read `data/ground_truth/`** — the
   circularity defense depends on it (INTERFACES §2).
6. **Detection thresholds are calibrated on the honest economy only**
   (DATA_GENERATION §6).
7. **No real personal data, ever.** Real countries and procedure categories;
   everything else fictional (ADR-015). Nothing secret is committed: no
   passwords, no API keys — `.env` only, `.env.example` documents.
8. **Flag bad ideas, including the team's.** Push back before building.
9. **Held-out temporal separation (ADR-027, replaces ADR-016's red-team
   isolation):** the held-out scenarios were authored and hash-committed
   2026-07-30, before any detection query existed. They stay outside the
   repo, unopened, until the one-shot evaluation (planned Aug 9). After the
   **detection freeze (Aug 6)**: no detection-query changes. After the
   **integration freeze (Aug 8)**: bug fixes and docs only. The claim this
   protocol supports is ordering, not independence — pitch wording in
   DATA_GENERATION §5; never state it stronger.
10. **No `Co-authored-by:` trailer may name a tool, bot, or third party** —
   human teammates only (CONTRIBUTING.md). This applies to every commit made
   with AI assistance in this repository, no exceptions.

## Working rules (permanent — added 2026-07-29 after three correction rounds)

1. **PROPAGATE, DON'T PATCH.** When correcting anything, search the whole
   repo for every other place that assumption appears and fix them all in
   the same pass. Report which files you touched and why. A fix applied only
   to the named file is an incomplete fix.
2. **BATCH ALL QUESTIONS.** If you need input, ask everything at once, at
   the start. Never surface one question, get an answer, then surface
   another that was knowable at the same time.
3. **NEVER ASSUME SILENTLY.** Before assuming, either verify it or write it
   into OPEN_QUESTIONS.md and say so explicitly in your reply. Unnamed
   assumptions baked into docs are our most expensive failure mode.
4. **STATE WHAT YOU DON'T KNOW.** Distinguish verified vs. inferred vs.
   unknowable-from-the-repo. Never describe an assumption as an observation.
5. **ACT ON REVERSIBLE THINGS.** Don't ask permission for anything a commit
   can undo — do it, then report it. Ask only about irreversible or
   human-only decisions (people, dates, money, scope cuts).
6. **SELF-CHECK BEFORE ENDING.** Before the final reply of any session,
   verify: changed files are mutually consistent; STATUS.md updated; new
   decisions in DECISIONS.md; new unknowns in OPEN_QUESTIONS.md; nothing
   invented is unverified. Report the result in one line.

## Conventions

- Git: short-lived branches, PRs into `main`, Conventional Commits, claim
  work before starting — see CONTRIBUTING.md. Commit authorship must be the
  real member doing the work (individual evaluation).
- IDs, CSV formats, JSON shapes, env vars: exactly as INTERFACES.md.
- Dates ISO 8601; money USD; snake_case properties; PascalCase labels;
  UPPER_SNAKE relationship types.
- Determinism: seeded RNG everywhere in the generator; no timestamps in
  generated artifacts (ADR-006).
- Memory profiles via `.env`: 8 GB machines 2G heap/1G pagecache; 16 GB+
  4G/2G. The 8 GB profile must always work.

## Doc map

STATUS (live snapshot — read first) · PROJECT_BRIEF (problem, 90 s) · DATA_MODEL (schema) · DETECTION_SPEC (six
typologies + FP modes; freezes Aug 6) · DATA_GENERATION (economy; fraud
layers; held-out protocol) · INTERFACES (module contracts — the most
important file) · DECISIONS (ADR log) · OPEN_QUESTIONS (assumptions parked,
with owners) · DEFENCE_AREAS (who answers what in Q&A) · MILESTONES
(schedule; freezes Aug 6/8) · PITCH (10-minute script) · DEMO_RUNBOOK
(offline demo + failure drills) · DAY2_PLAYBOOK (constraint shapes) ·
GLOSSARY (shared vocabulary) · HELDOUT_COMMITMENT (hash commitments).

## Environment facts (measured — ADR-002)

Lead's machine: 23.7 GB RAM, Ryzen 7 7435HS, Windows 11. git + gh present
and authenticated (`Don-Gabriel`). **Docker was not yet installed at
planning time** — first task of M1 on every machine. Other members' machines
unmeasured (OQ #10).
