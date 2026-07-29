# STATUS — snapshot, not a log

**Updated:** 2026-07-29 (build session, J Don Gabriel) · **Days to Day 1
(Aug 12): 14**

## Current milestone: M1 — walking skeleton (due Jul 30 EOD)

Exit test: fresh clone → `docker compose up` → browser shows node counts.
Plus (ADR-020): first boot must confirm GDS loads — `RETURN gds.version()`
returns 2.13.x — because the `NEO4J_PLUGINS` line is UNVERIFIED.

## DONE

- Planning docs + contracts (all of `docs/`), corrected and pushed
- Session protocol + working rules in CLAUDE.md; this STATUS flow
- Repo scaffold: generator/ graph/ loader/ detection/ api/ frontend/ data/,
  pyproject, schema.cypher
- docker-compose.yml + api/frontend Dockerfiles (NEO4J_PLUGINS marked
  UNVERIFIED — OQ #2)
- Generator v1: seeded honest economy + emergent fraud params; determinism
  tests green (ADR-021). No scenario overlays yet (waits on OQ #12); no
  planted cells yet (M3)
- Data-shape fixes (ADR-022/023): every owned device now edged (12,975
  USED_DEVICE edges, 0 orphans; 560 shared devices = 555 family / 5
  recycled); OWNS_STAKE_IN generated (25 honest / 10 hidden). Seed-42
  totals now 51.1k nodes / 193.7k rels / 7.4 MB

## IN PROGRESS

- (unclaimed) — next session picks from NEXT 3 below

## BLOCKED

- **Docker not installed on any of the 5 machines** — human task tonight;
  blocks compose testing, not code
- **OQ #12 attestation (Pavithra)** — blocks held-out scenario tooling in
  the generator and the PITCH claim-branch choice

## NEXT 3 (priority order)

1. Tonight's sync: record OQ #12 attestation under ADR-016; everyone
   installs Docker Desktop (append machine specs to ADR-002)
2. Implement `loader/` per INTERFACES §4 (wipe-and-load + manifest
   validation) → run the M1 exit test end-to-end
3. Confirm the UNVERIFIED `NEO4J_PLUGINS` line on first compose up
   (OQ #2) → then M2: generator distribution tuning + full-size dataset.
   M3 watch item (ADR-022): only ~5 recycled-identity device shares at
   seed 42 — thin for typology 5; calibrate recycling volume with the M3
   fraud work, don't tune it blind

## Decisions awaiting a human

- OQ #12: Pavithra's attestation (tonight's sync)
- Four GitHub handles in README.md
- OQ #7: adopt minimal CI? (team decision at sync)
