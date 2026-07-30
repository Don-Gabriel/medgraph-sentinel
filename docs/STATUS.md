# STATUS — snapshot, not a log

**Updated:** 2026-07-30 late (batch 2: freeze + API + console session,
J Don Gabriel) · **Days to Day 1 (Aug 12): 13**

## ⛔ THE DATASET IS FROZEN (ADR-031)

`data/` — 51,990 nodes / 197,251 relationships / 7.6 MB, seed 42, planted
cells + parallel recycling included — plus the exported **81 alerts /
2,098 IMPLICATES** (`alerts.csv`, `rel_implicates.csv`, pinned
`created_at 2026-07-30T00:00:00Z`) are the demo artifacts. Compose-up
loads alerts as data (ADR-029); no clone ever runs detection.

**Unfreeze cost, stated plainly:** any regeneration or detection re-run
= the FULL ADR-018 chain from the top (regenerate → load → detect →
export → rebuild narration cache → recommit as one unit) and eats a
rehearsal day. After Aug 8: demo-blocker emergency only. The narration
cache (Aug 3) is chain stage 2 — nothing regenerates between.

## Standing context

- **SOLO (ADR-027).** Held-out scenarios sealed outside the repo
  (hashes: HELDOUT_COMMITMENT.md, commit `290101e`) until the Aug 9
  one-shot. Claim = ordering, not independence (DATA_GENERATION §5).
- Rehearsal-weighted plan (MILESTONES): console → narration Aug 3 →
  **early cold-start Aug 4–5** → freezes Aug 6/8 → held-out Aug 9 →
  dress rehearsal Aug 10 (confirmation).

## DONE (2026-07-30, batch 2 — PRs #6, #7 + freeze commit)

- **API complete (INTERFACES §6):** stats/list/detail/subgraph(300 cap)/
  narration-fallback/PATCH/entities; 29 new tests (suite 64+); live
  smoke: list 18 ms, hops=1 subgraph 267–712 ms, hops=2 3–5 s (watch
  item — console defaults hops=1). Contract change: subgraph cap 300
  (owner decision).
- **Generator finished + dataset frozen (ADR-031):** scenario overlays
  (full §3, fixtures, byte-determinism proven), planted cells (3 ghost +
  3 credential), parallel recycling (3 impossible passport groups).
- **Dev-set results (frozen rules, nothing tuned):** planted cells 3/3
  caught at high for BOTH typologies 1 and 2; impossible groups 3/3 at
  high; kickback 6/13 brokers (unchanged misses = sub-median-volume
  steerers); low-severity FP tail is the documented honest-noise floor.
  Full table + honest findings: ADR-031.
- Honest economy still yields **zero medium+ alerts on every rule**.
- **Console COMPLETE (M2 exit passed):** queue (filters = counts,
  heat-ramp severity), Cytoscape hero view (ember-haloed implicated
  nodes, tuned cose — OQ #6 closed, type legend, hover/click inspect,
  async 2-hop expand), evidence panel (formatted summary_params, roles,
  narration with honest source tag), PATCH disposition with optimistic
  update. Visually verified at 1440/768; 0 console errors; fonts
  bundled offline (@fontsource); build 614 kB.

- **Narration COMPLETE (ADR-032, pulled forward from Aug 3):** all 81
  alerts carry committed pre-generated narrations (assistant session,
  canonical prompt template, prompt_sha256 pinned, zero API calls ever);
  UI tags them "pre-generated AI narration"; `/health` now checks cache
  completeness by alert-id set (`missing` surfaced, tested). **The
  ADR-018 chain is fully committed: dataset + alerts + narration cache.**
- **Cold-start prepared (ADR-033 single machine):** offline bundle built
  and staged; docs/COLD_START.md is the hand-run venue script; only the
  owner-physical steps remain (USB walk, network adapter, Aug 4–5 run).

## NEXT (priority order)

1. Owner-physical: EARLY COLD-START (Aug 4–5) per docs/COLD_START.md.
2. Aug 3: contingency + PITCH v3 + first full aloud pass of the
   DEFENCE_AREAS bank.
3. Freezes Aug 6/8, held-out one-shot Aug 9, rehearsals Aug 9–11 —
   unchanged.

## Decisions awaiting a human

- (none) — API key moot (ADR-032); backup laptop resolved (ADR-033:
  single machine, owner-owned contingency); OQ #14 moot for this build
  (dataset frozen with the planted post-revocation biller exercising
  the ramp).
