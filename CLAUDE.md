# CLAUDE.md — project memory for MedGraph Sentinel

Read this first in every session. The docs under `docs/` are the design;
this file is the standing context and rules.

## What this is

Fraud-intelligence graph over cross-border medical tourism: synthetic
economy → Neo4j graph → six detection typologies → investigator console.
Built by a 5-person team for the Hazzino Technologies State-Level Mega
Hackathon (Theni, Tamil Nadu):

- **Day 1 — Aug 12, 2026:** 10-minute pitch of a pre-built prototype to a
  technical jury and hiring recruiters; top 3–5 teams advance.
- **Day 2 — Aug 13, 2026:** live coding sprint with a surprise constraint.
- Venue network is assumed absent; the demo must run fully offline.
- This is a hiring drive: the repo, the commits, and each member's ability
  to explain any module aloud are the actual deliverables.
- Repo is private until the evening of Aug 11, then public.

## Stack (pinned — rationale in docs/DECISIONS.md)

- Neo4j **5.26 Community (LTS)** + GDS **2.13** (ADR-004), Cypher.
- Python **3.11**, FastAPI, Pydantic (ADR-003) for generator, loader,
  detection, API.
- React + Vite + Tailwind + Cytoscape.js (ADR-007).
- One Claude API call per alert for narration (`claude-opus-5`, official
  `anthropic` SDK), disk-cached and committed, deterministic fallback
  (ADR-010).
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
9. **Red-team isolation (ADR-016):** from 2026-07-29 the designated red-team
   member (Pavithra R, pending the OQ #12 attestation) does not read
   docs/DETECTION_SPEC.md or `detection/` rule code until the held-out
   evaluation results are committed. After the **detection freeze (Aug 6)**:
   no detection-query changes, and the red-team member does no detection
   work at all until the evaluation (ADR-012). After the **integration
   freeze (Aug 8)**: bug fixes and docs only.
10. **No `Co-authored-by:` trailer may name a tool, bot, or third party** —
   human teammates only (CONTRIBUTING.md). This applies to every commit made
   with AI assistance in this repository, no exceptions.

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

PROJECT_BRIEF (problem, 90 s) · DATA_MODEL (schema) · DETECTION_SPEC (six
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
