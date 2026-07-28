# narration_cache/ — COMMITTED demo asset (ADR-010 / ADR-018)

One `<alert_id>.json` per narrated alert, written only by the narration
builder as the last step of the one-way build chain:
dataset → load → detect → **build cache** → commit. Never edit by hand,
never rebuild partially. The API validates count-vs-alerts at startup and
fails loudly on mismatch. Currently empty: no alerts exist yet.
