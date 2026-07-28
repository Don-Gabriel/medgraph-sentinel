# loader/

Wipe-and-load of the committed dataset (`data/csv/` + `data/manifest.json`)
into Neo4j, after applying `graph/schema.cypher`. Runs as the one-shot
`seed` compose service and standalone as `python -m loader`.

Contract: [docs/INTERFACES.md](../docs/INTERFACES.md) §4. **Currently a
stub that exits 1** — M1 work item; claim it per CONTRIBUTING before
starting. Bulk-load mechanism benchmark is OQ #1.
