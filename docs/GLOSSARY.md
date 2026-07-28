# Glossary

One page. All five of us use exactly these words under questioning — fluid
roles make shared vocabulary load-bearing. If a term drifts in the code,
rename the code.

## Domain

- **Medical tourism** — traveling to another country for medical treatment,
  usually price- or waitlist-driven.
- **Corridor** — an origin-country → treatment-country flow (e.g. GB→IN for
  cardiac). Our economy has 5 treatment countries, ~10 origins.
- **Facilitator / broker** — the agency arranging a medical-tourism journey
  (clinic choice, travel, paperwork) for a commission. One word in this
  project: **broker**.
- **TPA (third-party administrator)** — a company processing claims on behalf
  of multiple insurers; sees cross-insurer flows, hence our likeliest buyer.
- **Accrediting body** — an organisation certifying clinic quality/standards;
  fictional in our data (`accreditation_status`).
- **Claim** — the bill submitted to an insurer for one procedure. The hub
  node of our model.
- **Ghost clinic** — a clinic existing on paper that bills for procedures
  never performed (typology 1).
- **Credential laundering** — reusing one licence number across multiple
  practitioner identities/jurisdictions, or billing after revocation
  (typology 2).
- **Kickback ring** — broker steers volume to clinics paying for referrals;
  closed by hidden ownership or shared banking (typology 3).
- **Template cloning / claim mill** — resubmitting one perfected claim
  package across many patients (typology 4).
- **Impossible travel** — one identity treated in two countries closer in
  time than physical travel allows (typology 5).
- **Circular payment** — money leaving a clinic and returning to its cluster
  via intermediary accounts (typology 6).
- **Shell account** — a `PaymentAccount` with no `OWNED_BY` edge; a conduit
  with no visible owner.
- **Typology** — one named fraud pattern with a defined graph signature and
  detection rule. We ship six.

## Graph & detection

- **Node / relationship (edge)** — Neo4j's records: entities and the typed,
  directed connections between them.
- **Label** — a node's type tag (`:Patient`, `:Claim`).
- **Cypher** — Neo4j's query language; patterns like
  `(c:Claim)-[:AT_CLINIC]->(k:Clinic)`.
- **Traversal** — walking edges from a starting node; "3 hops" = 3 edges out.
- **Subgraph** — the small slice of the graph relevant to one alert; what the
  console renders (never the full graph).
- **GDS (Graph Data Science library)** — Neo4j's algorithm plugin; we use its
  open-source tier, v2.13.
- **Projection** — GDS's in-memory copy of a slice of the graph that
  algorithms run against.
- **Community detection / Louvain** — unsupervised grouping of densely
  connected nodes; fraud rings show up as unusually dense communities.
- **PageRank** — importance score from the structure of incoming links; ranks
  influential brokers in the referral flow.
- **Betweenness centrality** — how often a node sits on shortest paths
  between others; finds *bridges* (hub brokers) regardless of volume.
- **WCC (weakly connected components)** — the graph's disconnected islands;
  sanity checks and candidate scoping.
- **Graph signature** — the structural shape a typology leaves in the graph
  (what we actually match on).
- **Rule / registry** — one typology's detection implementation + its YAML
  metadata; the registry is the folder of all rules (ADR-008).
- **Alert** — one scored finding written into the graph as an `:Alert` node
  `IMPLICATES`-linked to its evidence.
- **Score / severity** — 0–100 normalized suspicion; banded low/medium/high.
- **False positive (FP)** — an innocent structure matching a fraud signature;
  every rule documents its FP modes in DETECTION_SPEC.
- **Precision / recall** — of flagged items, how many were truly fraudulent /
  of truly fraudulent items, how many we flagged. Reported per fraud layer.

## Project-specific

- **Honest economy** — the synthetic world with no fraud parameters; the
  baseline detection is calibrated against.
- **Emergent fraud** — fraud arising from actor *incentive parameters*
  interacting, never placed as a labeled pattern (DATA_GENERATION §3).
- **Planted fraud** — explicitly templated, exactly labeled cells for
  typologies where emergence is unreliable (§4).
- **Held-out scenarios** — fraud scenarios authored after the detection
  freeze, outside the repo, hash-committed, evaluated once (§5).
- **Freeze** — a dated commit after which a document/module only changes for
  bug fixes: detection freeze Aug 6, integration freeze Aug 8.
- **Narration** — the plain-English explanation of an alert; one cached
  Claude call per alert with a deterministic offline fallback (ADR-010).
- **Walking skeleton** — M1: the thinnest end-to-end slice (tiny data, all
  services) proving the pipeline before any module gets deep.
