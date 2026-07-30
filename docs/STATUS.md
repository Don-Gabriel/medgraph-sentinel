# STATUS — snapshot, not a log

**Updated:** 2026-07-30 (solo-transition + detection session, J Don
Gabriel) · **Days to Day 1 (Aug 12): 13**

## Standing context (changed 2026-07-30 — read ADR-027)

- **SOLO.** No other member contributes. One person builds, documents,
  pitches, and runs Day 2. MILESTONES rewritten (~93–100 scheduled hours);
  anchored dates hold: detection freeze **Aug 6**, integration freeze
  **Aug 8**, dress rehearsal **Aug 10**.
- **Held-out protocol is temporal separation (ADR-027):** five scenarios
  authored + SHA-256-committed 2026-07-30 (commit `290101e`) BEFORE any
  detection query existed. Files live OUTSIDE the repo
  (`C:\WorkSpace\Private\medgraph-heldout\`) — **do not open/edit/delete
  until the one-shot Aug 9 evaluation.** Claim = ordering, not
  independence; exact pitch wording in DATA_GENERATION §5.
- Typologies 4 and 6 remain descoped (ADR-024). We ship 1, 2, 3, 5.

## DONE (this session, 2026-07-30 — branch claude/solo-implementer-transition-768b06)

- **PR #3 merged:** replan branch (M1 passed, loader, seed-42 dataset,
  GDS-baked image) is on main.
- **Team scaffolding stripped (ADR-027):** DEFENCE_AREAS → solo jury drill
  sheet; CONTRIBUTING solo; MILESTONES one-person hours incl. the returned
  ~24 h of pitch/demo/rehearsal work; DAY2_PLAYBOOK solo protocol
  (hard timers, rehearse-not-improvise); README/LICENSE/OQ propagated.
- **Held-out scenarios authored + hash-committed** before any detection
  query (overlay schema extended first — `contract:` commit; INTERFACES §3
  now expresses credential/identity scenarios).
- **ADR-028 (measured):** typology 3 drops centrality — exact betweenness
  131.6 s at 51k nodes AND worst steering discriminator (P@13 0.077 vs
  0.385 for top-clinic concentration); 8/13 steering brokers sit below
  median volume, invisible to topology scores. Sampled betweenness
  (samplingSize 2048: 94% top-50 agreement, 5% cost) is the documented
  fallback. Evidence: detection/benchmarks/typology3_centrality.md.
- **ADR-029 (proven):** alerts are committed data — detection/export.py →
  alerts.csv + rel_implicates.csv + manifest counts; loader loads them
  (optional stems, prefix-routed IMPLICATES); compose `seed` runs loader
  only. Round trip verified: detect → export → wipe-load (33/33 counts,
  7.2 s seed with alerts) → re-export **byte-identical**.
- **Detection layer real (ADR-030, M3 pulled forward):** registry runner
  (--rules/--dry-run/--created-at, idempotent per rule+version,
  deterministic ALT numbering, 200-entity cap) + four rules + shared
  travel_time_days config (OQ #4/#5 closed). Calibrated on the honest
  economy (fraud gates zeroed): **zero medium+ honest alerts per rule.**
- **Dev-set evaluation** (evaluation/ is the only ground-truth reader), 68
  alerts total: kickback precision 1.0, broker recall 6/13 (misses are the
  sub-median-volume steerers); impossible_travel 0/5 emergent recycled
  groups — **seed 42 contains zero temporally impossible recycled cases**
  (tightest cross-country gap 6 days), so the rule cannot catch them by
  construction; typologies 1/2 not evaluable until planted cells land.
- Tests 22 passed; dataset regenerated to sync manifest config_sha256
  (CSV bytes unchanged).

## BLOCKED

- (nothing hard-blocked; OQ #13 backup laptop and OQ #14 revoked-biller
  generator behavior are owner decisions, not blockers)

## NEXT 3 (priority order — MILESTONES Jul 31)

1. **Generator: scenario-overlay support (INTERFACES §3 incl. extensions)
   + planted cells for typologies 1/2 + recycling calibration** — planted
   cells must include tight-window recycled identities or typology 5 stays
   untestable (this session's measured finding); decide OQ #14 in the same
   pass; regenerate dev dataset + re-run dev evaluation (~8 h)
2. API alert endpoints against the real 68 alerts (Aug 1)
3. Console queue + Cytoscape drill-down (Aug 2; M2 exit)

## Decisions awaiting a human

- OQ #13: does a backup laptop exist? (affects DEMO_RUNBOOK drills)
- OQ #14: should the honest generator wind down revoked-doctor billing?
  (regenerates dataset; decide with Jul 31 planted-cell work)
- OQ #7: adopt minimal CI? (solo decision, ~1 h)
