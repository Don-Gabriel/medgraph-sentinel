"""CSV + manifest + ground-truth output per docs/INTERFACES.md §2.

Byte-determinism rules (ADR-006): UTF-8, \\n line endings, RFC 4180 via the
csv module, rows sorted on their key columns, money at 2dp, no timestamps.
"""
import csv
import json
from pathlib import Path

from . import __version__
from .economy import World


def _write_csv(path: Path, header: list[str], rows: list[list]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        out = csv.writer(fh, lineterminator="\n")
        out.writerow(header)
        out.writerows(rows)
    return len(rows)


def _fmt_money(x) -> str:
    return f"{float(x):.2f}"


def write_all(w: World, out_dir: Path, seed: int, config_sha256: str,
              ground_truth_rows: list[dict]) -> dict:
    csv_dir = out_dir / "csv"
    counts: dict[str, int] = {}

    def node(name: str, header: list[str], rows: list[list]):
        counts[name] = _write_csv(csv_dir / f"{name}.csv", header, sorted(rows))

    node("patients", ["id", "full_name", "dob", "gender", "passport_no"],
         [[p["id"], p["full_name"], p["dob"], p["gender"], p["passport_no"]]
          for p in w.patients])
    node("doctors", ["id", "full_name", "specialty"],
         [[d["id"], d["full_name"], d["specialty"]] for d in w.doctors])
    node("clinics", ["id", "name", "bed_count", "registration_date", "accreditation_status"],
         [[c["id"], c["name"], c["bed_count"], c["registration_date"],
           c["accreditation_status"]] for c in w.clinics])
    node("brokers", ["id", "name", "agency_name"],
         [[b["id"], b["name"], b["agency_name"]] for b in w.brokers])
    node("claims",
         ["id", "amount_usd", "procedure_date", "submission_date", "status",
          "line_item_count", "narrative_fingerprint"],
         [[c["id"], _fmt_money(c["amount_usd"]), c["procedure_date"], c["submission_date"],
           c["status"], c["line_item_count"], c["narrative_fingerprint"]] for c in w.claims])
    node("credentials",
         ["id", "license_no", "issuing_body", "issue_date", "status", "revocation_date"],
         [[c["id"], c["license_no"], c["issuing_body"], c["issue_date"], c["status"],
           c["revocation_date"]] for c in w.credentials])
    node("payment_accounts", ["id", "account_ref", "bank_name", "opened_date"],
         [[a["id"], a["account_ref"], a["bank_name"], a["opened_date"]] for a in w.accounts])
    node("devices", ["id", "device_hash", "device_type"],
         [[d["id"], d["device_hash"], d["device_type"]] for d in w.devices])
    node("addresses", ["id", "street", "city", "postcode"],
         [[a["id"], a["street"], a["city"], a["postcode"]] for a in w.addresses])
    node("procedures", ["id", "code", "category", "name", "base_cost_usd"],
         [[p["id"], p["code"], p["category"], p["name"], _fmt_money(p["base_cost_usd"])]
          for p in w.procedures])
    node("insurers", ["id", "name"], [[i["id"], i["name"]] for i in w.insurers])
    node("countries", ["code", "name", "role", "cost_multiplier"],
         [[c["code"], c["name"], c["role"], c["cost_multiplier"]] for c in w.countries])

    def rel(name: str, extra: list[str], rows: list[list]):
        counts[name] = _write_csv(csv_dir / f"{name}.csv",
                                  ["source_id", "target_id"] + extra, sorted(rows))

    rel("rel_resides_in", [], [[p["id"], p["home_country"]] for p in w.patients])
    rel("rel_used_device", ["first_seen", "last_seen"],
        [[pid, dev, lo.isoformat(), hi.isoformat()]
         for (pid, dev), (lo, hi) in w.used_device.items()])
    rel("rel_for_patient", [], [[c["id"], c["patient_id"]] for c in w.claims])
    rel("rel_at_clinic", [], [[c["id"], c["clinic_id"]] for c in w.claims])
    rel("rel_performed_by", [], [[c["id"], c["doctor_id"]] for c in w.claims])
    rel("rel_for_procedure", [], [[c["id"], c["procedure_id"]] for c in w.claims])
    rel("rel_billed_to", [], [[c["id"], c["insurer_id"]] for c in w.claims])
    rel("rel_arranged_by", ["commission_pct"],
        [[c["id"], c["broker_id"], c["commission_pct"]]
         for c in w.claims if c["broker_id"]])
    rel("rel_paid_to", [], [[c["id"], c["account_id"]] for c in w.claims])
    rel("rel_holds", [], [[c["doctor_id"], c["id"]] for c in w.credentials])
    rel("rel_issued_in", [], [[c["id"], c["country_code"]] for c in w.credentials])
    rel("rel_practises_at", ["since"],
        [[p["doctor_id"], p["clinic_id"], p["since"]] for p in w.practises])
    rel("rel_located_at", [], [[c["id"], c["address_id"]] for c in w.clinics])
    rel("rel_operates_from", [], [[b["id"], b["address_id"]] for b in w.brokers])
    rel("rel_in_country", [], [[a["id"], a["country_code"]] for a in w.addresses])
    rel("rel_owned_by", [],
        [[a["id"], a["owner_id"]] for a in w.accounts if a["owner_id"]])
    rel("rel_owns_stake_in", ["pct"],
        [[s["broker_id"], s["clinic_id"], s["pct"]] for s in w.owns_stake])
    rel("rel_transferred", ["amount_usd", "date"],
        [[t["src"], t["dst"], _fmt_money(t["amount_usd"]), t["date"]] for t in w.transfers])
    rel("rel_based_in", [], [[i["id"], i["country_code"]] for i in w.insurers])

    gt_dir = out_dir / "ground_truth"
    _write_csv(gt_dir / "actor_params.csv", ["actor_id", "param_name", "value"],
               sorted([[r["actor_id"], r["param_name"], r["value"]]
                       for r in ground_truth_rows]))
    _write_csv(gt_dir / "planted.csv", ["entity_id", "cell_id", "typology"], [])

    manifest = {
        "generator_version": __version__,
        "seed": seed,
        "config_sha256": config_sha256,
        "scenarios_applied": [],
        "counts": counts,
    }
    with open(out_dir / "manifest.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return manifest
