// MedGraph Sentinel — Neo4j schema DDL (constraints + indexes)
// MUST stay byte-for-byte in sync with docs/DATA_MODEL.md (that doc wins).
// Applied idempotently by the loader before any data load (INTERFACES §4).

// --- uniqueness constraints (auto-create backing indexes) ---
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

// --- indexes (each maps to a named query — see DATA_MODEL.md "Indexes") ---
// typology 2: credentials sharing a licence number — deliberately NOT unique
CREATE INDEX cred_license_no   IF NOT EXISTS FOR (n:Credential) ON (n.license_no);
// typology 5: patients sharing a passport
CREATE INDEX patient_passport  IF NOT EXISTS FOR (n:Patient)    ON (n.passport_no);
// typologies 2, 5, 6 + date-window queries
CREATE INDEX claim_proc_date   IF NOT EXISTS FOR (n:Claim)      ON (n.procedure_date);
CREATE INDEX claim_sub_date    IF NOT EXISTS FOR (n:Claim)      ON (n.submission_date);
// (claim_fingerprint index removed with typology 4's descope — ADR-024.
//  Every index here maps to a shipping query; re-add one line if typology 4
//  is revived on Day 2.)
// API alert queue filters
CREATE INDEX alert_status      IF NOT EXISTS FOR (n:Alert)      ON (n.status);
CREATE INDEX alert_typology    IF NOT EXISTS FOR (n:Alert)      ON (n.typology);
