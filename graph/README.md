# graph/

Neo4j schema DDL: `schema.cypher` (constraints + indexes). Byte-for-byte in
sync with [docs/DATA_MODEL.md](../docs/DATA_MODEL.md) — the doc wins;
change the doc first.

The loader (`loader/`, `python -m loader`) applies this file idempotently
before every load (INTERFACES §4). Nothing else lives here.
