"""Config schema (pydantic) + loader. The YAML is the tuning surface;
this file is the contract that catches a typo before it becomes a bad run."""
import hashlib
from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"


class Meta(BaseModel):
    version: str


class Window(BaseModel):
    start: date
    end: date

    @model_validator(mode="after")
    def _ordered(self):
        if self.start >= self.end:
            raise ValueError("window.start must precede window.end")
        return self


class TreatmentCountry(BaseModel):
    code: str = Field(pattern=r"^[A-Z]{2}$")
    name: str
    cost_multiplier: float = Field(gt=0)


class OriginCountry(BaseModel):
    code: str = Field(pattern=r"^[A-Z]{2}$")
    name: str
    outbound_weight: float = Field(gt=0)


class Countries(BaseModel):
    treatment: list[TreatmentCountry]
    origin: list[OriginCountry]


class CategoryCatalog(BaseModel):
    count: int = Field(gt=0)
    cost_mu: float
    cost_sigma: float = Field(gt=0)


class Populations(BaseModel):
    patients: int = Field(gt=0)
    doctors: int = Field(gt=0)
    clinics: int = Field(gt=0)
    brokers: int = Field(gt=0)
    insurers: int = Field(gt=0)


class Patients(BaseModel):
    return_rate: float = Field(ge=0, le=1)
    passport_null_rate: float = Field(ge=0, le=1)
    family_device_share: float = Field(ge=0, le=1)
    second_device_rate: float = Field(ge=0, le=1)


class Clinics(BaseModel):
    zipf_a: float = Field(gt=1)
    bed_zero_rate: float = Field(ge=0, le=1)
    accreditation: dict[str, float]
    shared_address_rate: float = Field(ge=0, le=1)
    accounts_min: int = Field(ge=1)
    accounts_max: int


class Doctors(BaseModel):
    affiliations_min: int = Field(ge=1)
    affiliations_max: int
    credentials_min: int = Field(ge=1)
    credentials_max: int
    revoked_rate: float = Field(ge=0, le=1)


class Brokers(BaseModel):
    zipf_a: float = Field(gt=1)
    arranged_share: float = Field(ge=0, le=1)
    commission_min_pct: float
    commission_max_pct: float
    accounts_min: int = Field(ge=1)
    accounts_max: int
    colocate_with_clinic_rate: float = Field(ge=0, le=1)
    stake_rate: float = Field(ge=0, le=1)
    stake_min_pct: float = Field(gt=0)
    stake_max_pct: float


class Claims(BaseModel):
    claims_per_journey_min: int = Field(ge=1)
    claims_per_journey_max: int
    ancillary_amount_min: float = Field(gt=0)
    ancillary_amount_max: float
    price_noise_sigma: float = Field(gt=0)
    submission_lag_min_days: int = Field(ge=0)
    submission_lag_max_days: int
    status_weights: dict[str, float]


class Transfers(BaseModel):
    commission_lag_days: int = Field(ge=0)


class Overbilling(BaseModel):
    clinic_rate: float = Field(ge=0, le=1)
    factor_min: float = Field(gt=1)
    factor_max: float
    claim_share_min: float = Field(ge=0, le=1)
    claim_share_max: float = Field(ge=0, le=1)


class Steering(BaseModel):
    broker_rate: float = Field(ge=0, le=1)
    greed_min: float = Field(ge=0, le=1)
    greed_max: float = Field(ge=0, le=1)
    partners_min: int = Field(ge=1)
    partners_max: int
    partner_overbilling_bias: float = Field(ge=1)
    side_commission_min_pct: float
    side_commission_max_pct: float
    stake_prob: float = Field(ge=0, le=1)
    stake_min_pct: float = Field(gt=0)
    stake_max_pct: float


class IdentityRecycling(BaseModel):
    broker_rate: float = Field(ge=0, le=1)
    reuse_min: float = Field(ge=0, le=1)
    reuse_max: float = Field(ge=0, le=1)
    # Share of recycled-clone events that ALSO get a parallel-billed journey:
    # a second clone of the same identity treated the SAME DAY in a DIFFERENT
    # treatment country (colluding clinics billing one recruited identity
    # simultaneously). This is what makes typology 5 genuinely testable —
    # sequential reuse alone never violates a whole-day travel table.
    parallel_share: float = Field(ge=0, le=1)


class ShellLayering(BaseModel):
    pair_rate: float = Field(ge=0, le=1)
    shells_min: int = Field(ge=1)
    shells_max: int
    attrition_min_pct: float
    attrition_max_pct: float
    recycle_prob: float = Field(ge=0, le=1)


class Fraud(BaseModel):
    overbilling: Overbilling
    steering: Steering
    identity_recycling: IdentityRecycling
    shell_layering: ShellLayering


class PlantedGhostClinics(BaseModel):
    cells: int = Field(ge=0)          # 0 = no planted ghost cells (honest run)
    patients_min: int = Field(ge=1)
    patients_max: int
    doctors_min: int = Field(ge=1)
    doctors_max: int
    feeder_share: float = Field(ge=0, le=1)   # share of journeys the feeder arranges
    payout_concentration: float = Field(ge=0, le=1)  # share paid to the hub account


class PlantedCredentialMills(BaseModel):
    cells: int = Field(ge=0)          # 0 = no planted credential cells
    doctors_min: int = Field(ge=2)    # cloned identities per licence number
    doctors_max: int
    journeys_min: int = Field(ge=1)   # journeys per clean identity
    journeys_max: int
    post_revocation_cells: int = Field(ge=0)  # cells whose original keeps billing
    post_rev_journeys_min: int = Field(ge=1)
    post_rev_journeys_max: int


class Planted(BaseModel):
    ghost_clinics: PlantedGhostClinics
    credential_mills: PlantedCredentialMills


class Config(BaseModel):
    meta: Meta
    window: Window
    countries: Countries
    gravity: dict[str, dict[str, float]]
    procedure_categories: dict[str, CategoryCatalog]
    category_weights: dict[str, float]
    populations: Populations
    patients: Patients
    clinics: Clinics
    doctors: Doctors
    brokers: Brokers
    claims: Claims
    transfers: Transfers
    # Shared with detection typology 5 (OQ #5): minimum whole travel days
    # between treatment countries. Optional so pre-existing configs stay
    # valid; the generator itself does not consume it (the impossible_travel
    # rule mirrors it — tests/test_detection_registry.py keeps them in sync).
    travel_time_days: dict[str, dict[str, int]] | None = None
    fraud: Fraud
    planted: Planted

    @model_validator(mode="after")
    def _cross_checks(self):
        cats = set(self.procedure_categories)
        if set(self.category_weights) != cats:
            raise ValueError("category_weights keys must match procedure_categories")
        origins = {c.code for c in self.countries.origin}
        treatments = {c.code for c in self.countries.treatment}
        if set(self.gravity) != origins:
            raise ValueError("gravity rows must match origin country codes")
        for origin, row in self.gravity.items():
            if set(row) != treatments:
                raise ValueError(f"gravity[{origin}] must cover all treatment countries")
        if self.travel_time_days is not None:
            if set(self.travel_time_days) != treatments:
                raise ValueError("travel_time_days rows must match treatment countries")
            for code, row in self.travel_time_days.items():
                if set(row) != treatments - {code}:
                    raise ValueError(
                        f"travel_time_days[{code}] must cover every OTHER treatment country")
                if any(v < 1 for v in row.values()):
                    raise ValueError("travel_time_days entries must be >= 1 whole day")
        return self


def load_config(path: Path | None = None) -> tuple[Config, str]:
    """Load + validate config; returns (config, sha256-of-file-bytes).

    The hash goes into data/manifest.json (ADR-006) so a dataset is always
    traceable to the exact config that produced it.
    """
    p = path or DEFAULT_CONFIG_PATH
    raw = p.read_bytes()
    cfg = Config.model_validate(yaml.safe_load(raw))
    return cfg, hashlib.sha256(raw).hexdigest()
