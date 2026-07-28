# data/ — committed, deterministic, never generated at boot (ADR-005/006)

- `csv/` — generator output (seed 42), the dataset every clone demos from.
  Regenerating it triggers the FULL ADR-018 chain (load → detect → narration
  cache → commit together).
- `manifest.json` — seed, config hash, per-file counts. No timestamps.
- `ground_truth/` — emergent-fraud actor params + planted-cell labels.
  **Read by the evaluation script ONLY — never by detection/, api/, or
  frontend/ (INTERFACES §2, enforced in review).**
- `scenarios/` — scenario overlay files; `scenarios/heldout/` stays empty
  until after the held-out evaluation (ADR-012/016).

Committed CSVs land at M2. Budget: < 50 MB total; reduce claim count rather
than adding Git LFS if it busts (owner decision Q7).
