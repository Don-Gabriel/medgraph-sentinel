"""Scenario overlays — the INTERFACES §3 schema (incl. the 2026-07-30
extensions: doctor/credential/patients-pool actor kinds, country pin,
journey doctor pin, pool:<ref> patients, transfers.count).

    python -m generator --seed 42 --out data/ --scenario s1.yaml --scenario s2.yaml

Design rules:

- Scenarios apply strictly AFTER the base generation (honest + emergent +
  planted), in sorted order of their `scenario` name, drawing from the same
  single numpy Generator — so the same seed + config + scenario SET is
  byte-identical (ADR-006) and base generation with no scenarios is
  bit-for-bit unaffected.
- Scenario actors take IDs from a reserved range (PAT_900001+, CLM_9000001+;
  World.scn_seq) so they can never collide with base entities.
- Journeys route through economy.emit_journey_claims — the same journey
  model as everything else.
- Ground truth (created entities + referenced existing actors) is returned
  for data/ground_truth/scenario_<name>.csv; actor `params` are appended to
  the actor_params.csv rows because they ARE emergent incentive parameters
  (evaluation derives kickback/recycling truth from that file).

Ambiguities in the written schema were resolved as follows (also listed in
generator/README.md):
- `recycled:<n>`: n source identities are created; journeys cycle through
  them; every use after a source's first creates a CLONE node (new id/alias,
  same passport/dob/device) — mirroring the emergent recycling mechanic.
  `pool:<ref>` reuses the SAME Patient nodes, per the schema comment.
- transfers `path`: entries are `<ref>.account` / `<existing id>.account`
  (first account of that actor, created if the actor has none), a raw
  `ACC_...` id, or the literal `shell` (one new unowned account per `shell`
  position, shared by all `count` transfers of the entry — layering chains
  reuse their conduits). `amount_usd` is the per-transfer amount at the
  first hop; each later hop applies `attrition_pct`.
- edges whose data lives on node records (HOLDS, ISSUED_IN, LOCATED_AT,
  OPERATES_FROM, RESIDES_IN, OWNED_BY on scenario-created rows) update the
  record so the writer emits exactly one row; every other DATA_MODEL type
  becomes a raw row in the matching rel_*.csv.
- an optional top-level `typology` key is tolerated (fills the third ground
  truth column; empty string when absent).
- broker `params.steering_greed` marks that broker's scenario journeys as
  steered with the given probability; side payments for those claims are
  materialized by fraud.side_payments over the scenario's claims only.
"""
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import yaml
from pydantic import BaseModel, Field, model_validator

from .economy import (CARE_DAYS, CLINIC_SUFFIXES, JourneyContext, World,
                      _price, _track_device, date_in, device_hash,
                      emit_journey_claims, money, pick)
from .narrative import _CLOSINGS, build_narrative, simhash64
from . import fraud as fraud_mod

# DATA_MODEL relationship type -> rel_*.csv stem + extra columns (order!)
REL_FILES = {
    "RESIDES_IN": ("rel_resides_in", []),
    "USED_DEVICE": ("rel_used_device", ["first_seen", "last_seen"]),
    "FOR_PATIENT": ("rel_for_patient", []),
    "AT_CLINIC": ("rel_at_clinic", []),
    "PERFORMED_BY": ("rel_performed_by", []),
    "FOR_PROCEDURE": ("rel_for_procedure", []),
    "BILLED_TO": ("rel_billed_to", []),
    "ARRANGED_BY": ("rel_arranged_by", ["commission_pct"]),
    "PAID_TO": ("rel_paid_to", []),
    "HOLDS": ("rel_holds", []),
    "ISSUED_IN": ("rel_issued_in", []),
    "PRACTISES_AT": ("rel_practises_at", ["since"]),
    "LOCATED_AT": ("rel_located_at", []),
    "OPERATES_FROM": ("rel_operates_from", []),
    "IN_COUNTRY": ("rel_in_country", []),
    "OWNED_BY": ("rel_owned_by", []),
    "OWNS_STAKE_IN": ("rel_owns_stake_in", ["pct"]),
    "TRANSFERRED": ("rel_transferred", ["amount_usd", "date"]),
    "BASED_IN": ("rel_based_in", []),
}

ACTOR_KINDS = {"clinic", "broker", "doctor", "credential", "patients"}


# ---------- schema (pydantic — a typo fails before any generation) ----------

class ScnActor(BaseModel):
    kind: str
    ref: str
    props: dict = Field(default_factory=dict)
    params: dict = Field(default_factory=dict)
    count: int | None = None  # patients pool only

    @model_validator(mode="after")
    def _check(self):
        if self.kind not in ACTOR_KINDS:
            raise ValueError(f"actor kind '{self.kind}' not in {sorted(ACTOR_KINDS)}")
        if self.kind == "patients" and (self.count is None or self.count < 1):
            raise ValueError(f"patients pool '{self.ref}' needs count >= 1")
        return self


class ScnEdge(BaseModel):
    type: str
    from_: str = Field(alias="from")
    to: str
    props: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check(self):
        if self.type not in REL_FILES:
            raise ValueError(f"edge type '{self.type}' is not a DATA_MODEL type")
        return self


class ScnJourneys(BaseModel):
    count: int = Field(ge=1)
    clinic: str
    broker: str | None = None
    doctor: str | None = None
    patients: str = "invented"  # invented | recycled:<n> | pool:<ref>
    category: str
    date_range: tuple[date, date]
    # ADR-037 (typology-4 substrate): emit this spec's claims as a claim
    # mill — ONE claim per journey, one procedure/narrative/price template
    # for the whole pack with tiny per-claim mutations, and 1-2 shared
    # submission devices. False = the normal journey model, untouched.
    clone_pack: bool = False

    @model_validator(mode="after")
    def _check(self):
        p = self.patients
        if p != "invented" and not p.startswith(("recycled:", "pool:")):
            raise ValueError(f"patients must be invented | recycled:<n> | pool:<ref>, got '{p}'")
        if p.startswith("recycled:") and int(p.split(":", 1)[1]) < 1:
            raise ValueError("recycled:<n> needs n >= 1")
        if self.date_range[0] > self.date_range[1]:
            raise ValueError("date_range start must not follow end")
        return self


class ScnTransfer(BaseModel):
    path: list[str] = Field(min_length=2)
    amount_usd: float = Field(gt=0)
    count: int = Field(default=1, ge=1)
    attrition_pct: float = Field(default=0, ge=0, lt=100)
    date_range: tuple[date, date]


class Scenario(BaseModel):
    scenario: str = Field(min_length=1)
    description: str = ""
    typology: str = ""  # optional; tolerated for ground-truth labeling
    actors: list[ScnActor] = Field(default_factory=list)
    edges: list[ScnEdge] = Field(default_factory=list)
    journeys: list[ScnJourneys] = Field(default_factory=list)
    transfers: list[ScnTransfer] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self):
        refs = [a.ref for a in self.actors]
        if len(refs) != len(set(refs)):
            raise ValueError("duplicate actor refs in scenario")
        return self


def load_scenario(path: Path) -> Scenario:
    return Scenario.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


# ---------- application ----------

class _Ctx:
    """Per-scenario resolution state."""

    def __init__(self, cfg, rng, fake, w: World, fp, scn: Scenario):
        self.cfg, self.rng, self.fake, self.w, self.fp, self.scn = cfg, rng, fake, w, fp, scn
        self.jctx = JourneyContext.build(cfg, w)
        self.by_ref: dict[str, dict] = {}      # ref -> actor record
        self.kind_of: dict[str, str] = {}      # ref -> kind
        self.pools: dict[str, list[dict]] = {}  # ref -> pool patient records
        self.created: list[str] = []           # entity ids created
        self.referenced: set[str] = set()      # existing ids touched
        self.gt_params: list[dict] = []        # rows for actor_params.csv
        self.claims: list[dict] = []           # claims emitted by this scenario
        self.clinics_by_id = {c["id"]: c for c in w.clinics}
        self.brokers_by_id = {b["id"]: b for b in w.brokers}
        self.doctors_by_id = {d["id"]: d for d in w.doctors}
        self.country_codes = {c["code"] for c in w.countries}
        self.treatment_codes = [c.code for c in cfg.countries.treatment]
        self.origin_codes = [c.code for c in cfg.countries.origin]
        ow = np.array([c.outbound_weight for c in cfg.countries.origin])
        self.origin_w = ow / ow.sum()
        ip = np.array([i["weight"] for i in w.insurers])
        self.ins_p = ip / ip.sum()


def apply_scenario(cfg, rng, fake, w: World, fp, scn: Scenario) -> list[dict]:
    """Apply one parsed scenario; returns its ground-truth rows."""
    ctx = _Ctx(cfg, rng, fake, w, fp, scn)
    for actor in scn.actors:
        _create_actor(ctx, actor)
    for edge in scn.edges:
        _apply_edge(ctx, edge)
    for spec in scn.journeys:
        _run_journeys(ctx, spec)
    # side payments for steered scenario claims (broker params.steering_greed)
    steered = [c for c in ctx.claims if c["steered_by"]]
    if steered:
        fraud_mod.side_payments(cfg, rng, w, fp, claims=steered)
    for spec in scn.transfers:
        _run_transfers(ctx, spec)
    fp.ground_truth.extend(ctx.gt_params)
    seen: set[str] = set()
    rows = []
    for eid in ctx.created + sorted(ctx.referenced):
        if eid not in seen:
            seen.add(eid)
            rows.append({"entity_id": eid, "cell_id": scn.scenario,
                         "typology": scn.typology})
    return rows


# ---------- actors ----------

def _pin_country(ctx: _Ctx, props: dict, default_pool: list[str],
                 weights=None) -> str:
    code = props.get("country")
    if code is None:
        return pick(ctx.rng, default_pool, weights)
    if code not in ctx.country_codes:
        raise ValueError(f"scenario '{ctx.scn.scenario}': unknown country '{code}'")
    return code


def _create_actor(ctx: _Ctx, a: ScnActor) -> None:
    w, rng, fake, cfg = ctx.w, ctx.rng, ctx.fake, ctx.cfg
    props = dict(a.props)
    if a.kind == "clinic":
        country = _pin_country(ctx, props, ctx.treatment_codes)
        cid = w.scn_seq["CLI"].take()
        address_id = _scn_address(ctx, country)
        clinic = {
            "id": cid,
            "name": props.get("name", f"{fake.last_name()} {pick(rng, CLINIC_SUFFIXES)}"),
            "bed_count": int(props.get("bed_count",
                                       0 if rng.random() < cfg.clinics.bed_zero_rate
                                       else int(rng.lognormal(3.5, 0.8)) + 5)),
            "registration_date": str(props.get(
                "registration_date",
                date_in(rng, date(2010, 1, 1), cfg.window.start).isoformat())),
            "accreditation_status": props.get("accreditation_status", "provisional"),
            "country_code": country,
            "address_id": address_id,
            "account_ids": [_scn_account(ctx, "clinic", cid)],
            "size_weight": 0.0,
        }
        w.clinics.append(clinic)
        w.clinic_doctors[cid] = []
        ctx.clinics_by_id[cid] = clinic
        record = clinic
    elif a.kind == "broker":
        country = _pin_country(ctx, props, ctx.treatment_codes)
        bid = w.scn_seq["BRK"].take()
        broker = {
            "id": bid,
            "name": props.get("name", fake.name()),
            "agency_name": props.get("agency_name", f"{fake.last_name()} Medical Travel"),
            "address_id": _scn_address(ctx, country),
            "account_ids": [_scn_account(ctx, "broker", bid)],
            "weight": 0.0,
            "country_code": country,
        }
        w.brokers.append(broker)
        ctx.brokers_by_id[bid] = broker
        record = broker
    elif a.kind == "doctor":
        did = w.scn_seq["DOC"].take()
        doctor = {
            "id": did,
            "full_name": props.get("full_name", f"Dr. {fake.name()}"),
            "specialty": props.get("specialty", pick(rng, list(cfg.category_weights))),
            "clinic_ids": [],
        }
        w.doctors.append(doctor)
        ctx.doctors_by_id[did] = doctor
        record = doctor
    elif a.kind == "credential":
        crid = w.scn_seq["CRD"].take()
        license_no = props.get("license_no", f"MC-XX{rng.integers(10000, 99999)}")
        country = props.get("country") or _embedded_country(ctx, license_no)
        cred = {
            "id": crid,
            "license_no": license_no,
            "issuing_body": props.get("issuing_body", _council(w, country)),
            "issue_date": str(props.get(
                "issue_date", date_in(rng, date(2005, 1, 1), date(2024, 12, 31)).isoformat())),
            "status": props.get("status", "active"),
            "revocation_date": str(props.get("revocation_date", "")),
            "country_code": country,
            "doctor_id": "",  # a HOLDS edge assigns the holder
        }
        w.credentials.append(cred)
        record = cred
    else:  # patients pool: same Patient nodes reused across journeys
        country = props.get("country")
        pool = []
        for _ in range(a.count):
            pool.append(_new_patient(ctx, home=country))
        ctx.pools[a.ref] = pool
        record = {"id": None, "pool": pool}
    if record.get("id"):
        ctx.created.append(record["id"])
    ctx.by_ref[a.ref] = record
    ctx.kind_of[a.ref] = a.kind
    for pname, value in a.params.items():
        actor_id = record["id"]
        if actor_id is None:
            raise ValueError(f"params not supported on patients pool '{a.ref}'")
        ctx.gt_params.append({"actor_id": actor_id, "param_name": pname, "value": value})


def _scn_address(ctx: _Ctx, country: str) -> str:
    """Reserved-range address + IN_COUNTRY (mirrors World.new_address)."""
    w, rng, fake = ctx.w, ctx.rng, ctx.fake
    from .economy import CITIES
    adr = {
        "id": w.scn_seq["ADR"].take(),
        "street": fake.street_address(),
        "city": pick(rng, CITIES[country]) if country in CITIES else fake.city(),
        "postcode": fake.postcode(),
        "country_code": country,
    }
    w.addresses.append(adr)
    ctx.created.append(adr["id"])
    return adr["id"]


def _scn_account(ctx: _Ctx, owner_kind: str | None, owner_id: str | None) -> str:
    w, rng, fake, cfg = ctx.w, ctx.rng, ctx.fake, ctx.cfg
    acc = {
        "id": w.scn_seq["ACC"].take(),
        "account_ref": f"MG{rng.integers(10**15, 10**16 - 1)}",
        "bank_name": f"{fake.last_name()} Bank",
        "opened_date": date_in(rng, date(2015, 1, 1), cfg.window.start).isoformat(),
        "owner_kind": owner_kind,
        "owner_id": owner_id,
    }
    w.accounts.append(acc)
    ctx.created.append(acc["id"])
    return acc["id"]


def _new_patient(ctx: _Ctx, home: str | None = None, source: dict | None = None) -> dict:
    """Invented patient (or a clone of `source` for recycled journeys)."""
    w, rng, fake = ctx.w, ctx.rng, ctx.fake
    pid = w.scn_seq["PAT"].take()
    if source is not None:
        patient = {
            "id": pid,
            "full_name": fake.name(),  # new alias, same identity artifacts
            "dob": source["dob"],
            "gender": source["gender"],
            "passport_no": source["passport_no"],
            "home_country": source["home_country"],
            "device_ids": [pick(rng, source["device_ids"])],
        }
    else:
        home = home or pick(rng, ctx.origin_codes, ctx.origin_w)
        dev_id = w.scn_seq["DEV"].take()
        w.devices.append({"id": dev_id, "device_hash": device_hash(dev_id),
                          "device_type": pick(rng, ["mobile", "desktop", "tablet"],
                                              np.array([0.55, 0.30, 0.15]))})
        ctx.created.append(dev_id)
        patient = {
            "id": pid,
            "full_name": fake.name(),
            "dob": date_in(rng, date(1950, 1, 1), date(2005, 12, 31)).isoformat(),
            "gender": pick(rng, ["F", "M", "X"], np.array([0.49, 0.49, 0.02])),
            "passport_no": f"{home}{rng.integers(1000000, 9999999)}",
            "home_country": home,
            "device_ids": [dev_id],
        }
    w.patients.append(patient)
    ctx.created.append(pid)
    return patient


def _embedded_country(ctx: _Ctx, license_no: str) -> str:
    """Honest licence numbers embed their issuing country (MC-XX#####)."""
    if license_no.startswith("MC-") and license_no[3:5] in ctx.country_codes:
        return license_no[3:5]
    raise ValueError(
        f"scenario '{ctx.scn.scenario}': credential '{license_no}' needs an "
        "explicit props.country (no country code embedded in the number)")


def _council(w: World, code: str) -> str:
    name = next(c["name"] for c in w.countries if c["code"] == code)
    return f"Medical Council of {name}"


# ---------- refs / edges ----------

def _resolve(ctx: _Ctx, token: str) -> dict:
    """ref or existing entity id -> record (clinic/broker/doctor/credential/
    patient/country)."""
    if token in ctx.by_ref:
        return ctx.by_ref[token]
    if token in ctx.country_codes:
        return {"id": token, "kind": "country"}
    for table, key in ((ctx.clinics_by_id, "clinic"), (ctx.brokers_by_id, "broker"),
                       (ctx.doctors_by_id, "doctor")):
        if token in table:
            ctx.referenced.add(token)
            return table[token]
    for coll in (ctx.w.credentials, ctx.w.patients, ctx.w.accounts,
                 ctx.w.devices, ctx.w.addresses):
        for rec in coll:
            if rec["id"] == token:
                ctx.referenced.add(token)
                return rec
    raise ValueError(f"scenario '{ctx.scn.scenario}': unknown ref or id '{token}'")


def _apply_edge(ctx: _Ctx, e: ScnEdge) -> None:
    w = ctx.w
    src = _resolve(ctx, e.from_)
    dst = _resolve(ctx, e.to)
    t, props = e.type, e.props
    if t == "HOLDS":  # doctor -> credential: set the holder on the record
        dst["doctor_id"] = src["id"]
        return
    if t == "ISSUED_IN":  # credential -> country
        src["country_code"] = dst["id"]
        return
    if t == "PRACTISES_AT":
        w.practises.append({"doctor_id": src["id"], "clinic_id": dst["id"],
                            "since": str(props.get("since",
                                                   ctx.cfg.window.start.isoformat()))})
        return
    if t == "OWNS_STAKE_IN":
        w.owns_stake.append({"broker_id": src["id"], "clinic_id": dst["id"],
                             "pct": float(props.get("pct", 25.0))})
        return
    if t == "TRANSFERRED":
        w.transfers.append({
            "src": _account_of(ctx, e.from_), "dst": _account_of(ctx, e.to),
            "amount_usd": money(props["amount_usd"]),
            "date": str(props.get("date", ctx.cfg.window.start.isoformat()))})
        return
    if t == "USED_DEVICE":
        first = date.fromisoformat(str(props.get("first_seen",
                                                 ctx.cfg.window.start.isoformat())))
        last = date.fromisoformat(str(props.get("last_seen", first.isoformat())))
        w.used_device[(src["id"], dst["id"])] = [first, last]
        return
    if t == "RESIDES_IN" and "home_country" in src:
        src["home_country"] = dst["id"]
        return
    if t == "OWNED_BY" and "owner_id" in src:
        src["owner_id"] = dst["id"]
        src["owner_kind"] = ctx.kind_of.get(e.to, "clinic")
        return
    # generic fallback: raw row into the matching rel file (claim-star types,
    # LOCATED_AT/OPERATES_FROM/IN_COUNTRY to pre-existing addresses, ...)
    stem, extra_cols = REL_FILES[t]
    row = [src["id"], dst["id"]] + [str(props.get(c, "")) for c in extra_cols]
    w.extra_rels.setdefault(stem, []).append(row)


def _account_of(ctx: _Ctx, token: str) -> str:
    """`<ref>.account` / `<id>.account` -> first account (created if none);
    raw ACC_ id -> itself; `shell` handled by the transfer walker."""
    if token.startswith("ACC_"):
        ctx.referenced.add(token)
        return token
    base = token[:-8] if token.endswith(".account") else token
    rec = _resolve(ctx, base)
    if not rec.get("account_ids"):
        kind = ctx.kind_of.get(base) or ("clinic" if rec["id"].startswith("CLI_")
                                         else "broker")
        rec["account_ids"] = [_scn_account(ctx, kind, rec["id"])]
    return rec["account_ids"][0]


# ---------- journeys ----------

def _run_journeys(ctx: _Ctx, spec: ScnJourneys) -> None:
    cfg, rng, w = ctx.cfg, ctx.rng, ctx.w
    clinic = _resolve(ctx, spec.clinic)
    broker = _resolve(ctx, spec.broker) if spec.broker else None
    pinned_doctor = _resolve(ctx, spec.doctor) if spec.doctor else None
    if spec.category not in cfg.category_weights:
        raise ValueError(f"scenario '{ctx.scn.scenario}': unknown category "
                         f"'{spec.category}'")
    if not clinic.get("account_ids"):
        clinic["account_ids"] = [_scn_account(ctx, "clinic", clinic["id"])]
    if broker is not None and not broker.get("account_ids"):
        broker["account_ids"] = [_scn_account(ctx, "broker", broker["id"])]

    # patient source
    mode = spec.patients
    recycled_sources: list[dict] = []
    if mode.startswith("recycled:"):
        n = int(mode.split(":", 1)[1])
        recycled_sources = [None] * n  # created lazily on first use
    steer = None
    if broker is not None:
        greed = next((p["value"] for p in ctx.gt_params
                      if p["actor_id"] == broker["id"]
                      and p["param_name"] == "steering_greed"), None)
        if greed is not None:
            steer = float(greed)
            _ensure_steering_entry(ctx, broker, clinic)

    # clone packs share one claim template + submission devices (ADR-037);
    # drawn ONCE per spec so every claim in the pack is near-identical
    pack = _clone_pack_template(ctx, spec, clinic) if spec.clone_pack else None

    for i in range(spec.count):
        if mode == "invented":
            patient = _new_patient(ctx)
        elif mode.startswith("pool:"):
            pool = ctx.pools.get(mode.split(":", 1)[1])
            if pool is None:
                raise ValueError(f"scenario '{ctx.scn.scenario}': unknown pool "
                                 f"'{mode}'")
            patient = pool[i % len(pool)]  # same Patient nodes each use
        else:  # recycled:<n>
            slot = i % len(recycled_sources)
            if recycled_sources[slot] is None:
                recycled_sources[slot] = _new_patient(ctx)
                patient = recycled_sources[slot]
            else:
                patient = _new_patient(ctx, source=recycled_sources[slot])

        doctor = pinned_doctor
        if doctor is None:
            doctor = _scn_doctor_for(ctx, clinic, spec.category)
        _ensure_practises(ctx, doctor, clinic)

        if pack is not None:
            claim = _emit_clone_claim(ctx, spec, pack, i, patient=patient,
                                      clinic=clinic, doctor=doctor, broker=broker)
            ctx.claims.append(claim)
            ctx.created.append(claim["id"])
            continue
        insurer = pick(rng, w.insurers, ctx.ins_p)
        commission = (money(rng.uniform(cfg.brokers.commission_min_pct,
                                        cfg.brokers.commission_max_pct))
                      if broker else None)
        care_lo, care_hi = CARE_DAYS[spec.category]
        steered = bool(steer is not None and rng.random() < steer)
        claims = emit_journey_claims(
            cfg, rng, w, ctx.jctx, patient=patient, clinic=clinic, doctor=doctor,
            procedure=pick(rng, ctx.jctx.procs_by_cat[spec.category]),
            category=spec.category, insurer=insurer, broker=broker,
            commission=commission,
            account_id=pick(rng, clinic["account_ids"]),
            proc_date=date_in(rng, spec.date_range[0], spec.date_range[1]),
            days_in_care=int(rng.integers(care_lo, care_hi + 1)),
            device_id=pick(rng, patient["device_ids"]),
            over=None, steered=steered, claim_seq=w.scn_seq["CLM"])
        ctx.claims.extend(claims)
        ctx.created.extend(c["id"] for c in claims)


def _clone_pack_template(ctx: _Ctx, spec: ScnJourneys, clinic: dict) -> dict:
    """One template per journeys-spec: the mill's perfected claim package
    (DETECTION_SPEC §4). Same procedure, narrative, price base and
    line-item count for every claim; 2 shared submission devices."""
    rng, w = ctx.rng, ctx.w
    procedure = pick(rng, ctx.jctx.procs_by_cat[spec.category])
    care_lo, care_hi = CARE_DAYS[spec.category]
    days = int(rng.integers(care_lo, care_hi + 1))
    devices = []
    for _ in range(2):
        dev_id = w.scn_seq["DEV"].take()
        w.devices.append({"id": dev_id, "device_hash": device_hash(dev_id),
                          "device_type": "desktop"})  # the mill's office PCs
        ctx.created.append(dev_id)
        devices.append(dev_id)
    return {
        "procedure": procedure,
        "narrative": build_narrative(rng, procedure["name"], clinic["name"], days),
        "base_amount": _price(rng, ctx.cfg, procedure["base_cost_usd"],
                              ctx.jctx.cmult[clinic["country_code"]]),
        "line_items": int(rng.integers(3, 13)),
        "devices": devices,
    }


def _emit_clone_claim(ctx: _Ctx, spec: ScnJourneys, pack: dict, i: int, *,
                      patient: dict, clinic: dict, doctor: dict,
                      broker: dict | None) -> dict:
    """One near-identical clone of the pack template: names swapped, amount
    jittered ±2%, and roughly half the claims swap the closing sentence —
    small SimHash Hamming distance, never statistical glow."""
    cfg, rng, w = ctx.cfg, ctx.rng, ctx.w
    narrative = pack["narrative"]
    # 30%: hand-edited closing (measured Hamming 10-33 from the template —
    # at the honest floor, so these escape the rule and honestly so);
    # 70%: the lazy bulk, byte-identical → Hamming 0 (honest floor is 10)
    if rng.random() < 0.3:
        sentences = narrative.rsplit(". ", 1)
        narrative = sentences[0] + ". " + pick(rng, _CLOSINGS)
    amount = money(pack["base_amount"] * float(rng.uniform(0.98, 1.02)))
    claim_date = date_in(rng, spec.date_range[0], spec.date_range[1])
    submission = claim_date + timedelta(
        days=int(rng.integers(cfg.claims.submission_lag_min_days,
                              cfg.claims.submission_lag_max_days + 1)))
    insurer = pick(rng, w.insurers, ctx.ins_p)
    commission = (money(rng.uniform(cfg.brokers.commission_min_pct,
                                    cfg.brokers.commission_max_pct))
                  if broker else None)
    device_id = pack["devices"][i % len(pack["devices"])]
    account_id = pick(rng, clinic["account_ids"])
    claim = {
        "id": w.scn_seq["CLM"].take(),
        "amount_usd": amount,
        "procedure_date": claim_date.isoformat(),
        "submission_date": submission.isoformat(),
        "status": pick(rng, ctx.jctx.status_names, ctx.jctx.status_p),
        "line_item_count": pack["line_items"],
        "narrative_fingerprint": simhash64(narrative),
        "patient_id": patient["id"],
        "clinic_id": clinic["id"],
        "doctor_id": doctor["id"],
        "procedure_id": pack["procedure"]["id"],
        "insurer_id": insurer["id"],
        "broker_id": broker["id"] if broker else "",
        "commission_pct": commission if broker else "",
        "account_id": account_id,
        "steered_by": "",
    }
    w.claims.append(claim)
    _track_device(w, patient["id"], device_id, claim_date)
    if broker:
        w.transfers.append({
            "src": account_id,
            "dst": pick(rng, broker["account_ids"]),
            "amount_usd": money(amount * commission / 100.0),
            "date": (submission + timedelta(days=cfg.transfers.commission_lag_days)
                     ).isoformat(),
        })
    return claim


def _scn_doctor_for(ctx: _Ctx, clinic: dict, category: str) -> dict:
    """Journey model doctor assignment, scenario flavour: reuse the clinic's
    roster when one exists, otherwise attach a matching-specialty doctor from
    the base population (deterministic pick)."""
    roster = ctx.w.clinic_doctors.get(clinic["id"], [])
    matching = [d for d in roster if d["specialty"] == category]
    if matching:
        return pick(ctx.rng, matching)
    if roster:
        return pick(ctx.rng, roster)
    doctor = pick(ctx.rng, ctx.w.doctors)
    ctx.w.clinic_doctors.setdefault(clinic["id"], []).append(doctor)
    ctx.referenced.add(doctor["id"])
    return doctor


def _ensure_practises(ctx: _Ctx, doctor: dict, clinic: dict) -> None:
    for row in ctx.w.practises:
        if row["doctor_id"] == doctor["id"] and row["clinic_id"] == clinic["id"]:
            return
    ctx.w.practises.append({"doctor_id": doctor["id"], "clinic_id": clinic["id"],
                            "since": ctx.cfg.window.start.isoformat()})


def _ensure_steering_entry(ctx: _Ctx, broker: dict, clinic: dict) -> None:
    """fraud.side_payments needs an fp.steering entry for a steering broker;
    build one from scenario params + config-range draws."""
    f = ctx.cfg.fraud
    params = {p["param_name"]: p["value"] for p in ctx.gt_params
              if p["actor_id"] == broker["id"]}
    entry = ctx.fp.steering.get(broker["id"])
    if entry is None:
        entry = {
            "greed": float(params["steering_greed"]),
            "partners": [],
            "side_pct": float(params.get(
                "side_commission_pct",
                round(float(ctx.rng.uniform(f.steering.side_commission_min_pct,
                                            f.steering.side_commission_max_pct)), 2))),
            "layered": "shell_layering" in params,
            "shells": int(params.get("shell_layering", 0) or 1),
            "attrition_pct": float(params.get(
                "attrition_pct",
                round(float(ctx.rng.uniform(f.shell_layering.attrition_min_pct,
                                            f.shell_layering.attrition_max_pct)), 2))),
        }
        ctx.fp.steering[broker["id"]] = entry
    if clinic["id"] not in entry["partners"]:
        entry["partners"].append(clinic["id"])
        # keep exactly one steering_partners row per broker (latest set wins)
        ctx.gt_params = [p for p in ctx.gt_params
                         if not (p["actor_id"] == broker["id"]
                                 and p["param_name"] == "steering_partners")]
        ctx.gt_params.append({"actor_id": broker["id"],
                              "param_name": "steering_partners",
                              "value": "|".join(entry["partners"])})


# ---------- transfers ----------

def _run_transfers(ctx: _Ctx, spec: ScnTransfer) -> None:
    w, rng = ctx.w, ctx.rng
    # resolve the path once: shells are one account per `shell` position,
    # shared by all `count` transfers of this entry
    hops: list[str] = []
    for token in spec.path:
        if token == "shell":
            hops.append(_scn_account(ctx, None, None))  # no OWNED_BY: a shell
        else:
            hops.append(_account_of(ctx, token))
    dates = sorted(date_in(rng, spec.date_range[0], spec.date_range[1])
                   for _ in range(spec.count))
    for d in dates:
        amount = spec.amount_usd
        hop_date = d
        for src, dst in zip(hops, hops[1:]):
            w.transfers.append({"src": src, "dst": dst,
                                "amount_usd": money(amount),
                                "date": hop_date.isoformat()})
            amount = amount * (1 - spec.attrition_pct / 100.0)
            hop_date = hop_date + timedelta(days=int(rng.integers(1, 6)))
