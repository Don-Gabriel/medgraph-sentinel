"""Claim narratives + the SimHash fingerprint.

Narratives are assembled from templated fragments so honest claims are
similar-but-not-identical; template-cloned claims (a fraud typology) would
be near-identical. Fingerprint: 64-bit SimHash over word 3-gram shingles,
rendered as 16 hex chars (DATA_MODEL.md Claim.narrative_fingerprint).
SimHash-first decision: OQ #3.
"""
import hashlib

# Curated, invented-but-plausible procedure base names per category.
PROC_NAMES = {
    "cardiac": [
        "Coronary Artery Bypass Graft", "Percutaneous Coronary Intervention",
        "Aortic Valve Replacement", "Mitral Valve Repair", "Cardiac Ablation",
        "Pacemaker Implantation", "Carotid Endarterectomy", "Septal Defect Closure",
    ],
    "orthopaedic": [
        "Total Knee Replacement", "Total Hip Replacement", "Spinal Fusion",
        "Rotator Cuff Repair", "ACL Reconstruction", "Lumbar Discectomy",
        "Shoulder Arthroscopy", "Ankle Fixation",
    ],
    "cosmetic": [
        "Rhinoplasty", "Abdominoplasty", "Blepharoplasty", "Liposuction",
        "Hair Transplantation", "Breast Augmentation", "Facelift", "Otoplasty",
    ],
    "dental": [
        "Dental Implant Placement", "Full Mouth Rehabilitation", "Sinus Lift",
        "Bone Graft", "Zirconia Crown Restoration", "Root Canal Retreatment",
        "Veneer Placement", "Wisdom Tooth Extraction",
    ],
    "fertility": [
        "In Vitro Fertilisation Cycle", "Intracytoplasmic Sperm Injection",
        "Frozen Embryo Transfer", "Egg Retrieval", "Intrauterine Insemination",
        "Ovarian Reserve Assessment", "Hysteroscopic Polypectomy", "Embryo Cryopreservation",
    ],
    "oncology": [
        "Tumour Resection", "Chemotherapy Cycle", "Radiotherapy Course",
        "Radical Prostatectomy", "Mastectomy", "Colorectal Resection",
        "Thyroidectomy", "Lymph Node Dissection",
    ],
}

CODE_PREFIX = {
    "cardiac": "CAR", "orthopaedic": "ORT", "cosmetic": "COS",
    "dental": "DEN", "fertility": "FER", "oncology": "ONC",
}

_OPENINGS = [
    "Patient presented with", "Patient was referred for", "Elective admission for",
    "Scheduled treatment for", "Patient admitted with",
]
_COURSES = [
    "procedure completed without complication", "an uneventful intraoperative course",
    "standard post-operative recovery", "satisfactory clinical progress",
    "routine follow-up scheduled",
]
_CLOSINGS = [
    "Discharged in stable condition.", "Discharged with medication plan.",
    "Follow-up advised in 14 days.", "Referred for physiotherapy.",
    "Cleared for return travel.",
]


def variant_name(base: str, i: int) -> str:
    """Expand curated base names to the configured catalog size."""
    suffixes = ["", " - Bilateral", " - Revision", " - Stage II", " - Minimally Invasive"]
    return base + suffixes[i % len(suffixes)]


def build_narrative(rng, procedure_name: str, clinic_name: str, days_in_care: int) -> str:
    pick = lambda options: options[int(rng.integers(0, len(options)))]
    return (
        f"{pick(_OPENINGS)} {procedure_name.lower()} at {clinic_name}. "
        f"Inpatient course of {days_in_care} days with {pick(_COURSES)}. "
        f"{pick(_CLOSINGS)}"
    )


def simhash64(text: str) -> str:
    """64-bit SimHash over word 3-gram shingles, as 16 hex chars.

    Near-identical texts differ in few bits (small Hamming distance) —
    exactly the property typology 4 needs. Pure stdlib, deterministic.
    """
    words = text.lower().split()
    shingles = (
        [" ".join(words[i : i + 3]) for i in range(len(words) - 2)] if len(words) >= 3 else words
    )
    v = [0] * 64
    for sh in shingles:
        h = int.from_bytes(hashlib.md5(sh.encode()).digest()[:8], "big")
        for bit in range(64):
            v[bit] += 1 if (h >> bit) & 1 else -1
    out = 0
    for bit in range(64):
        if v[bit] > 0:
            out |= 1 << bit
    return f"{out:016x}"
