# Data Model

Canonical definition of every node label, relationship type, property, and the
Neo4j constraints and indexes. **If code and this document disagree, this
document wins — fix the code or PR a change to this file (see
[INTERFACES.md](INTERFACES.md) change protocol).**

Conventions:

- All IDs are strings with a type prefix and zero-padded number:
  `PAT_000001`, `CLM_0000001` (claims use 7 digits, everything else 6).
  Country uses ISO 3166-1 alpha-2 codes (`IN`, `TH`, `TR`, `AE`, `SG`, …) as
  its ID.
- All dates are ISO 8601 strings (`2025-11-30`) stored as Neo4j `date` values;
  timestamps as `datetime`.
- All money is USD (`amount_usd`, float). Currency conversion is out of scope;
  the generator prices in USD directly.
- Property names are `snake_case`. Labels and relationship types follow Neo4j
  convention: `PascalCase` labels, `UPPER_SNAKE` relationships.

## Node labels

### Patient
| property | type | notes |
|---|---|---|
| id | string | `PAT_` prefix, unique |
| full_name | string | Faker-generated, fully fictional |
| dob | date | |
| gender | string | `F` / `M` / `X` |
| passport_no | string | nullable; fictional format `AA1234567`. **Deliberately not unique** — shared passports across Patient nodes are a fraud signal (typology 5) |

### Doctor
| property | type | notes |
|---|---|---|
| id | string | `DOC_` prefix, unique |
| full_name | string | |
| specialty | string | one of the six procedure categories |

### Clinic
| property | type | notes |
|---|---|---|
| id | string | `CLI_` prefix, unique |
| name | string | fictional |
| bed_count | int | 0 is legal (day clinic) — and a ghost-clinic feature |
| registration_date | date | |
| accreditation_status | string | `accredited` / `provisional` / `none` |

### Broker
| property | type | notes |
|---|---|---|
| id | string | `BRK_` prefix, unique |
| name | string | |
| agency_name | string | |

### Claim
| property | type | notes |
|---|---|---|
| id | string | `CLM_` prefix (7 digits), unique |
| amount_usd | float | billed amount |
| procedure_date | date | when treatment allegedly occurred |
| submission_date | date | when claim reached the insurer; ≥ procedure_date |
| status | string | `submitted` / `approved` / `rejected` |
| line_item_count | int | number of billed line items |
| narrative_fingerprint | string | 16-hex-char locality-sensitive hash (SimHash, ADR-021) of the claim narrative; near-identical narratives → small Hamming distance. **Consumed only by descoped typology 4 (ADR-024)** — ships in the data as next-build substrate; no shipping rule reads it |

### Credential
| property | type | notes |
|---|---|---|
| id | string | `CRD_` prefix, unique |
| license_no | string | **indexed, deliberately not unique** — one licence number across several Credential/Doctor identities is the laundering signal (typology 2) |
| issuing_body | string | fictional, e.g. "Medical Council of …" |
| issue_date | date | |
| status | string | `active` / `revoked` / `suspended` |
| revocation_date | date | nullable; set iff status ≠ active |

### PaymentAccount
| property | type | notes |
|---|---|---|
| id | string | `ACC_` prefix, unique |
| account_ref | string | fictional IBAN-like string |
| bank_name | string | fictional |
| opened_date | date | |

An account with **no `OWNED_BY` edge is a shell account** — that absence is
data, not an error (descoped typology 6; typology 3's shared-infrastructure
signature still traverses these accounts).

### Device
| property | type | notes |
|---|---|---|
| id | string | `DEV_` prefix, unique |
| device_hash | string | fictional browser/device fingerprint |
| device_type | string | `mobile` / `desktop` / `tablet` |

### Address
| property | type | notes |
|---|---|---|
| id | string | `ADR_` prefix, unique |
| street | string | |
| city | string | real cities in corridor countries |
| postcode | string | fictional |

### Procedure
| property | type | notes |
|---|---|---|
| id | string | `PRC_` prefix, unique |
| code | string | invented scheme `CAR-014`, `ORT-002`, … (category prefix + number) |
| category | string | `cardiac` / `orthopaedic` / `cosmetic` / `dental` / `fertility` / `oncology` |
| name | string | plausible procedure name |
| base_cost_usd | float | reference price before country multiplier |

### Insurer
| property | type | notes |
|---|---|---|
| id | string | `INS_` prefix, unique |
| name | string | fictional |

### Country
| property | type | notes |
|---|---|---|
| code | string | ISO 3166-1 alpha-2, unique — this is the node's ID |
| name | string | |
| role | string | `treatment` / `origin` / `both` — corridor role in our economy |
| cost_multiplier | float | price level vs. base cost (treatment countries) |

### Alert *(written by the detection layer, not the generator)*
| property | type | notes |
|---|---|---|
| id | string | `ALT_` prefix, unique |
| typology | string | rule key, e.g. `ghost_clinic` (see DETECTION_SPEC) |
| rule_version | string | version of the rule that produced it |
| score | float | 0–100 normalized suspicion score |
| severity | string | `low` / `medium` / `high` derived from score bands |
| status | string | `new` / `reviewed` / `dismissed` (investigator-set) |
| note | string | free-text investigator note, default `""` |
| summary_params | string | JSON string of the evidence numbers the narration/template needs |
| created_at | datetime | when the detection run wrote it |

## Relationship types

| relationship | direction | properties | meaning |
|---|---|---|---|
| `RESIDES_IN` | (Patient)→(Country) | — | home country |
| `USED_DEVICE` | (Patient)→(Device) | first_seen: date, last_seen: date | device used on the claims portal; shared devices across "unrelated" patients are a signal |
| `FOR_PATIENT` | (Claim)→(Patient) | — | who was treated |
| `AT_CLINIC` | (Claim)→(Clinic) | — | where |
| `PERFORMED_BY` | (Claim)→(Doctor) | — | by whom |
| `FOR_PROCEDURE` | (Claim)→(Procedure) | — | what |
| `BILLED_TO` | (Claim)→(Insurer) | — | who pays |
| `ARRANGED_BY` | (Claim)→(Broker) | commission_pct: float | facilitated claims (~65% of claims have one) |
| `PAID_TO` | (Claim)→(PaymentAccount) | — | payout destination |
| `HOLDS` | (Doctor)→(Credential) | — | |
| `ISSUED_IN` | (Credential)→(Country) | — | issuing jurisdiction |
| `PRACTISES_AT` | (Doctor)→(Clinic) | since: date | |
| `LOCATED_AT` | (Clinic)→(Address) | — | |
| `OPERATES_FROM` | (Broker)→(Address) | — | broker office; broker/clinic address sharing is a signal |
| `IN_COUNTRY` | (Address)→(Country) | — | |
| `OWNED_BY` | (PaymentAccount)→(Clinic \| Broker) | — | account ownership; absence ⇒ shell |
| `OWNS_STAKE_IN` | (Broker)→(Clinic) | pct: float | declared or hidden ownership (sparse) |
| `TRANSFERRED` | (PaymentAccount)→(PaymentAccount) | amount_usd: float, date: date | inter-account money movement |
| `BASED_IN` | (Insurer)→(Country) | — | |
| `IMPLICATES` | (Alert)→(any entity node) | role: string | detection output; `role` labels the entity's part in the pattern, e.g. `hub_account`, `cloned_claim` |

## Constraints (Neo4j 5.x syntax)

One uniqueness constraint per node label on its ID (uniqueness constraints
auto-create a backing index):

```cypher
CREATE CONSTRAINT patient_id  IF NOT EXISTS FOR (n:Patient)        REQUIRE n.id   IS UNIQUE;
CREATE CONSTRAINT doctor_id   IF NOT EXISTS FOR (n:Doctor)         REQUIRE n.id   IS UNIQUE;
CREATE CONSTRAINT clinic_id   IF NOT EXISTS FOR (n:Clinic)         REQUIRE n.id   IS UNIQUE;
CREATE CONSTRAINT broker_id   IF NOT EXISTS FOR (n:Broker)         REQUIRE n.id   IS UNIQUE;
CREATE CONSTRAINT claim_id    IF NOT EXISTS FOR (n:Claim)          REQUIRE n.id   IS UNIQUE;
CREATE CONSTRAINT cred_id     IF NOT EXISTS FOR (n:Credential)     REQUIRE n.id   IS UNIQUE;
CREATE CONSTRAINT account_id  IF NOT EXISTS FOR (n:PaymentAccount) REQUIRE n.id   IS UNIQUE;
CREATE CONSTRAINT device_id   IF NOT EXISTS FOR (n:Device)         REQUIRE n.id   IS UNIQUE;
CREATE CONSTRAINT address_id  IF NOT EXISTS FOR (n:Address)        REQUIRE n.id   IS UNIQUE;
CREATE CONSTRAINT proc_id     IF NOT EXISTS FOR (n:Procedure)      REQUIRE n.id   IS UNIQUE;
CREATE CONSTRAINT insurer_id  IF NOT EXISTS FOR (n:Insurer)        REQUIRE n.id   IS UNIQUE;
CREATE CONSTRAINT country_code IF NOT EXISTS FOR (n:Country)       REQUIRE n.code IS UNIQUE;
CREATE CONSTRAINT alert_id    IF NOT EXISTS FOR (n:Alert)          REQUIRE n.id   IS UNIQUE;
```

## Indexes

Chosen for the access paths in DETECTION_SPEC and the API — each index exists
because a specific query needs it (be ready to name that query when asked):

```cypher
// typology 2: find credentials sharing a licence number — NOT unique, by design
CREATE INDEX cred_license_no  IF NOT EXISTS FOR (n:Credential) ON (n.license_no);
// typology 5: find patients sharing a passport
CREATE INDEX patient_passport IF NOT EXISTS FOR (n:Patient)    ON (n.passport_no);
// typologies 2, 5, 6 + date-window queries
CREATE INDEX claim_proc_date  IF NOT EXISTS FOR (n:Claim)      ON (n.procedure_date);
CREATE INDEX claim_sub_date   IF NOT EXISTS FOR (n:Claim)      ON (n.submission_date);
// (claim_fingerprint index removed with typology 4's descope — ADR-024.
//  Every index here maps to a shipping query; re-add one line if typology 4
//  is revived on Day 2.)
// API alert queue filters
CREATE INDEX alert_status     IF NOT EXISTS FOR (n:Alert)      ON (n.status);
CREATE INDEX alert_typology   IF NOT EXISTS FOR (n:Alert)      ON (n.typology);
```

The exact DDL will live in `graph/schema.cypher` (created in the build phase);
that file must stay byte-for-byte in sync with this document.

## Design notes (defend these under questioning)

- **Claim-centric star:** Claim is the hub connecting patient, clinic, doctor,
  procedure, insurer, broker, and payout account. Every typology traverses
  through claims, so the star keeps traversals short (1–2 hops).
- **Signals live in shared endpoints, not in flags.** There is no
  `is_fraud` property anywhere in the model. Suspicion is *structural*:
  shared licence numbers, shared devices, shared addresses, shared payout
  accounts, payment cycles. This is the core thesis of the project.
- **Passport/licence deliberately non-unique:** a uniqueness constraint would
  make the fraud we're hunting impossible to represent.
- **Alerts are first-class graph citizens:** detection output is written back
  as `Alert` nodes with `IMPLICATES` edges rather than exported to a file.
  The console then reads alerts and expands evidence with plain Cypher, and a
  new Day-2 rule needs zero API/frontend changes to surface its alerts (see
  DECISIONS ADR-008).
- **What breaks at 10M nodes:** these indexes and queries hold; exact
  betweenness centrality (O(n·m)) does not — you'd switch to sampled
  betweenness, and batch feature extraction would move to scheduled GDS
  pipelines. Louvain and the targeted queries scale fine. Neo4j Community's
  single-database, no-RBAC limits bite before the algorithms do.
