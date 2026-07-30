"""Typology 2 — credential laundering (DETECTION_SPEC §2).

Three targeted sub-queries, one rule:

(a) One licence number held by more than one doctor. FP guard from the
    spec: a hit only counts inside a group of credentials sharing the same
    issuing body OR the same issuing country — two different councils can
    both issue "MC-4471" and that is a format collision, not laundering.
(b) Claims performed after the doctor's credential was revoked, with a
    grace window for revocation-date entry lag, and only when the doctor
    holds no other credential that was still active on the procedure date
    (a doctor legitimately licensed elsewhere is sub-signal (c)'s job, not
    fraud by itself). Severity is tiered by post-revocation claim VOLUME:
    the honest economy keeps retired doctors on clinic rosters, so mere
    existence of post-revocation billing (up to 29 claims at seed 42) is
    honest noise and stays low; the spec's "starts at high" is reserved
    for systematic billing beyond anything the honest world produces.
    Calibration measurements and the reasoning: detection/README.md.
(c) Jurisdiction shopping: a credential issued in a country where the
    doctor has no practice, while the doctor's claims occur in 2+ other
    countries.

Sub-signals (b) and (c) merge into one alert per doctor; (a) is one alert
per licence group.
"""
from collections import defaultdict

from .common import scale

Q_SHARED_LICENSE = """
MATCH (d:Doctor)-[:HOLDS]->(cr:Credential)-[:ISSUED_IN]->(co:Country)
WITH cr.license_no AS lic,
     collect({doctor: d.id, cred: cr.id, body: cr.issuing_body,
              country: co.code, status: cr.status}) AS rows
WHERE size(rows) > 1
RETURN lic, rows
"""
Q_BILLING_DOCTORS = """
MATCH (c:Claim)-[:PERFORMED_BY]->(d:Doctor)
WHERE d.id IN $ids
RETURN d.id AS doctor, count(c) AS n_claims
"""
Q_POST_REVOCATION = """
MATCH (d:Doctor)-[:HOLDS]->(cr:Credential)
WHERE cr.status = 'revoked' AND cr.revocation_date IS NOT NULL
MATCH (clm:Claim)-[:PERFORMED_BY]->(d)
WHERE clm.procedure_date > cr.revocation_date + duration({days: $grace_days})
  AND NOT EXISTS {
    MATCH (d)-[:HOLDS]->(other:Credential)
    WHERE other <> cr
      AND (other.status = 'active'
           OR (other.revocation_date IS NOT NULL
               AND other.revocation_date > clm.procedure_date))
  }
WITH d, cr, clm
ORDER BY clm.procedure_date, clm.id
WITH d, cr, collect(clm.id) AS claim_ids, min(clm.procedure_date) AS first_claim
RETURN d.id AS doctor, cr.id AS cred, toString(cr.revocation_date) AS revoked_on,
       claim_ids,
       duration.inDays(cr.revocation_date, first_claim).days AS first_gap_days
"""
Q_JURISDICTION_SHOPPING = """
MATCH (d:Doctor)-[:HOLDS]->(cr:Credential)-[:ISSUED_IN]->(issue_co:Country)
WHERE NOT EXISTS {
  MATCH (d)-[:PRACTISES_AT]->(:Clinic)-[:LOCATED_AT]->(:Address)
        -[:IN_COUNTRY]->(issue_co)
}
MATCH (clm:Claim)-[:PERFORMED_BY]->(d)
MATCH (clm)-[:AT_CLINIC]->(:Clinic)-[:LOCATED_AT]->(:Address)
      -[:IN_COUNTRY]->(claim_co:Country)
WHERE claim_co <> issue_co
WITH d, cr, issue_co, collect(DISTINCT claim_co.code) AS claim_countries,
     collect(DISTINCT clm.id) AS claim_ids
WHERE size(claim_countries) >= $shopping_min_countries
RETURN d.id AS doctor, cr.id AS cred, issue_co.code AS issued_in,
       claim_countries, claim_ids
"""


def _shared_license_drafts(session, params: dict) -> list[dict]:
    drafts = []
    groups = [(r["lic"], [dict(x) for x in r["rows"]])
              for r in session.run(Q_SHARED_LICENSE)]
    all_doctors = sorted({row["doctor"] for _, rows in groups for row in rows})
    billing = {r["doctor"]: r["n_claims"]
               for r in session.run(Q_BILLING_DOCTORS, ids=all_doctors)}
    for lic, rows in groups:
        # FP guard: keep only credentials that share issuing body or issuing
        # country with at least one OTHER credential in the group.
        by_body, by_country = defaultdict(list), defaultdict(list)
        for row in rows:
            by_body[row["body"]].append(row)
            by_country[row["country"]].append(row)
        qualifying = [row for row in rows
                      if len(by_body[row["body"]]) > 1
                      or len(by_country[row["country"]]) > 1]
        doctors = sorted({row["doctor"] for row in qualifying})
        if len(doctors) < 2:
            continue  # format collision across unrelated issuers — guard holds
        if len(doctors) == 2:
            score = params["shared_two_score"]
        elif len(doctors) == 3:
            score = params["shared_three_score"]
        else:
            score = params["shared_many_score"]
        countries = sorted({row["country"] for row in qualifying})
        if len(countries) > 1:
            score += params["cross_country_bonus"]
        actively_billing = [d for d in doctors if billing.get(d, 0) > 0]
        if len(actively_billing) >= 2:
            score += params["active_billing_bonus"]
        creds = sorted({row["cred"] for row in qualifying})
        drafts.append({
            "anchor_id": creds[0],
            "score": score,
            "summary_params": {
                "signal": "shared_license",
                "license_no": lic,
                "holder_count": len(doctors),
                "issuing_countries": countries,
                "issuing_bodies": sorted({row["body"] for row in qualifying}),
                "actively_billing_holders": len(actively_billing),
            },
            "implicated": ([{"id": c, "role": "shared_license"} for c in creds]
                           + [{"id": d, "role": "license_holder"} for d in doctors]),
        })
    return drafts


def _doctor_drafts(session, params: dict) -> list[dict]:
    per_doctor: dict[str, dict] = {}
    for r in session.run(Q_POST_REVOCATION, grace_days=params["grace_days"]):
        recent = r["first_gap_days"] <= params["recent_days"]
        # Calibration on the honest economy (see YAML): existence alone is
        # low; volume beyond the honest ceiling is what escalates to high.
        n = len(r["claim_ids"])
        score = (params["post_revocation_base"]
                 + params["volume_ramp_points"]
                 * scale(n, params["volume_lo_claims"], params["volume_hi_claims"]))
        if recent:
            score += params["recent_bonus"]
        per_doctor.setdefault(r["doctor"], {"signals": [], "scores": [],
                                            "implicated": [], "summary": {}})
        d = per_doctor[r["doctor"]]
        d["signals"].append("post_revocation_billing")
        d["scores"].append(score)
        d["summary"].update({
            "revoked_credential": r["cred"],
            "revoked_on": r["revoked_on"],
            "days_from_revocation_to_first_claim": r["first_gap_days"],
            "post_revocation_claims": len(r["claim_ids"]),
            "revocation_recent": recent,
        })
        d["implicated"] += ([{"id": r["cred"], "role": "revoked_credential"}]
                            + [{"id": c, "role": "post_revocation_claim"}
                               for c in r["claim_ids"]])
    for r in session.run(Q_JURISDICTION_SHOPPING,
                         shopping_min_countries=params["shopping_min_countries"]):
        extra = len(r["claim_countries"]) - params["shopping_min_countries"]
        score = params["shopping_score"] + extra * params["extra_country_bonus"]
        per_doctor.setdefault(r["doctor"], {"signals": [], "scores": [],
                                            "implicated": [], "summary": {}})
        d = per_doctor[r["doctor"]]
        d["signals"].append("jurisdiction_shopping")
        d["scores"].append(score)
        d["summary"].update({
            "shopped_credential": r["cred"],
            "issued_in": r["issued_in"],
            "claim_countries": sorted(r["claim_countries"]),
        })
        d["implicated"] += ([{"id": r["cred"], "role": "shopped_credential"}]
                            + [{"id": c, "role": "cross_border_claim"}
                               for c in sorted(r["claim_ids"])])
    drafts = []
    for doctor in sorted(per_doctor):
        d = per_doctor[doctor]
        # Strongest signal carries the alert; a second *different* signal on
        # the same doctor adds a flat stack bonus — explainable, no double
        # counting (two revoked credentials are one behaviour, not two).
        score = max(d["scores"])
        if len(set(d["signals"])) > 1:
            score += params["costack_bonus"]
        seen, implicated = set(), [{"id": doctor, "role": "suspect_doctor"}]
        for e in d["implicated"]:
            if e["id"] not in seen:
                seen.add(e["id"])
                implicated.append(e)
        drafts.append({
            "anchor_id": doctor,
            "score": score,
            "summary_params": {"signal": "+".join(sorted(set(d["signals"]))),
                               **d["summary"]},
            "implicated": implicated,
        })
    return drafts


def run(session, params: dict) -> list[dict]:
    return _shared_license_drafts(session, params) + _doctor_drafts(session, params)
