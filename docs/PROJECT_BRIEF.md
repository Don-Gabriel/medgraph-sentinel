# MedGraph Sentinel — Project Brief

*The 90-second version. If you read nothing else in this repo, read this.*

## The problem

Every year millions of patients travel abroad for medical treatment — cardiac
surgery in India, dental work in Turkey, fertility treatment in Thailand. A
single patient journey touches five separate record-keepers: the patient's home
country, the treating country, the insurer, the facilitator (broker) who
arranged the trip, and the accrediting body that vouches for the clinic. **No
one of them sees the whole chain.**

Fraud lives in that gap: ghost clinics billing for procedures never performed,
doctors practising on revoked licences, brokers recycling patient identities
across insurers, claim mills submitting the same documentation with the names
changed.

## Why current tools miss it

Today's fraud detection is *per-claim*: one insurer scores one claim against
its own historical data. That catches a claim that looks wrong. But organised
fraud is engineered so that **every individual record looks fine**. The doctor
has a licence number. The clinic has an address. The claim amount is plausible.
The fraud is only visible in the *relationships* — one licence number behind
four doctor identities, thirty clinics funneling payouts into one bank
account, money leaving a clinic and coming back through a shell.

Fraud is a network. Detection that can't see the network can't see the fraud.

## What MedGraph Sentinel does

1. **Builds the graph.** Patients, doctors, clinics, brokers, claims,
   credentials, payment accounts, devices, and addresses become nodes in a
   Neo4j graph database; every real-world relationship becomes an edge.
2. **Finds suspicious structure.** Four detection typologies — ghost
   clinics, credential laundering, kickback rings, impossible travel —
   implemented as graph algorithms (community detection, centrality) and
   targeted graph queries. Each finding becomes a scored, explainable
   alert. (Two further typologies are specified as the roadmap —
   DETECTION_SPEC, ADR-024.)
3. **Explains it to a human.** An investigator console shows an alert queue;
   clicking an alert reveals the exact subgraph of evidence and a plain-English
   narration of why this pattern is suspicious.

The prototype runs on a fully synthetic economy of ~50,000 entities across
five real medical-tourism corridors (India, Thailand, Turkey, UAE, Singapore).
No real patient data is used or implied, anywhere.

## Who would buy this

- **Insurers and reinsurers** — the parties losing the money. Cross-border
  claims are their fastest-growing loss category with the least tooling.
- **Third-party administrators (TPAs)** — process claims for many insurers and
  are ideally placed to see cross-insurer patterns.
- **Accreditation bodies** — need evidence to revoke accreditation from
  clinics that exist only on paper.
- **National health authorities** — jurisdictions marketing themselves as
  medical-tourism destinations have a reputational stake in policing them.

The honest scaling story: this prototype is single-tenant on synthetic data.
A production deployment would need a data-sharing consortium (the hard part is
legal, not technical), entity resolution on messy real-world identifiers, and
Neo4j Enterprise for access control between competing insurers. We know where
the prototype ends and the product begins — ask us about it.
