# Open Questions

Things we were tempted to assume but didn't. Each has an owner-by-date and a
resolution path. When resolved: move the answer into DECISIONS.md (as an ADR
or a note on an existing one) and strike it here with a pointer.

| # | question | resolve by | how |
|---|---|---|---|
| 1 | **Bulk-load mechanism:** `LOAD CSV` vs `neo4j-admin database import` for ~50k nodes / ~140k rels. Admin import is faster but requires an offline DB and a different CSV header format; LOAD CSV is simpler and probably fast enough at this scale. | Jul 31 | whoever builds the loader benchmarks both on the real dataset; record numbers in DECISIONS |
| 2 | **Docker image plugin + memory syntax:** exact `NEO4J_PLUGINS` value for GDS and the heap/pagecache env-var names for the 5.26 image. High confidence these exist; we do not write them from memory (ADR-004). | Jul 30 | read the Neo4j operations manual Docker pages while writing docker-compose.yml; paste the doc URL into the compose file comments |
| 3 | **Narrative fingerprint algorithm:** SimHash vs MinHash over narrative shingles for typology 4. Need: small Hamming/Jaccard distance for template clones, robust to name swaps. | Aug 3 | implement SimHash first (simpler, fixed-width, fits the indexed-property design); test clone-vs-honest separation on generated narratives; fall back to GDS Node Similarity if separation is poor |
| 4 | **Score normalization + threshold calibration:** how each rule's raw features map to 0–100, and how thresholds are set against the honest economy (DATA_GENERATION §6). | Aug 5, before freeze | tune on honest-actor FP rates; document per-rule in the rule YAML; sanity-check score distributions |
| 5 | **Impossible-travel time table:** minimum corridor travel times in days (we store dates, not times). Must be written down before the freeze since typology 5 depends on it. | Aug 5 | small static table in generator config, shared with the rule; conservative values (flag only clearly impossible pairs) |
| 6 | **Cytoscape layout:** built-in `cose` vs the `cose-bilkent`/`fcose` extension for 50–200 node evidence subgraphs. | Aug 4 | try built-in first; add extension only if layouts are unreadable; check extension maintenance status before adopting |
| 7 | **CI:** is a minimal GitHub Actions workflow (ruff + pytest + frontend build) worth it? Leaning yes — it's a work-sample signal and catches integration breaks between five parallel contributors. Costs setup time on day 2. | Jul 30 | team decision at standup; if yes, keep it under 5 min runtime |
| 8 | **Narration top-N:** how many alerts get real Claude narrations vs template fallback (cost is trivial; the question is cache freshness discipline after detection re-runs). | Aug 7 | pick N ≈ 40 after seeing real alert counts; rebuild cache as part of the Aug 8 freeze checklist |
| 9 | **Demo laptop identity:** which physical machine presents on Aug 12 (assumed: this 24 GB machine). Its Docker install + full offline rehearsal must happen on *that* machine, not an equivalent one. | Aug 8 | confirm at team sync; DEMO_RUNBOOK is executed on that machine on Aug 10 |
| 10 | **Team hardware inventory:** RAM/OS/Docker status of the other four machines (only the lead's machine is measured — ADR-002). | Jul 30 | each member appends a line to ADR-002 when installing Docker |
| 11 | **GDS memory settings for projections:** whether default heap profiles suffice for Louvain/betweenness on our graph, or whether we need explicit projection sizing. Expected fine at 50k nodes; verify, don't assume. | Aug 4 | run `gds.graph.project` + algorithms under the 8 GB profile; record peak heap in DECISIONS |
