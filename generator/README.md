# generator/

The synthetic medical-tourism economy. Design:
[docs/DATA_GENERATION.md](../docs/DATA_GENERATION.md); output contract:
[docs/INTERFACES.md](../docs/INTERFACES.md) §2–3.

```
python -m generator --seed 42 --out data/
```

- `config.yaml` — every tunable distribution (the M2 tuning surface and the
  Day-2 scale knobs). `config.py` validates it and hashes it for the
  manifest.
- `economy.py` — honest actors + journeys. Fraud parameters distort honest
  decisions inline (steering, recycling, overbilling) — fraud is never a
  separate labeled code path.
- `fraud.py` — emergent parameter assignment + kickback/shell/recycle
  transfers. Ground truth = the parameter record, written to
  `data/ground_truth/` (evaluation-only — INTERFACES §2).
- `narrative.py` — templated claim narratives + 64-bit SimHash fingerprint
  (OQ #3: SimHash-first).
- `writer.py` — deterministic CSVs + manifest (sorted rows, 2dp money, no
  timestamps — ADR-006).

**Not implemented yet, on purpose:** planted cells (M3,
DATA_GENERATION §4) — `planted.csv` is emitted with a header only; scenario
overlays / `--scenario` (waits on the OQ #12 attestation, ADR-016).

**Known v1 simplifications** (M2 tuning items, tracked in STATUS): Faker
names/streets are en-US regardless of country; category choice is
age-independent; no duplicate-name-spelling noise yet. Distribution realism
is tuned to DATA_GENERATION §2 at M2, judged by the M2 exit test.
