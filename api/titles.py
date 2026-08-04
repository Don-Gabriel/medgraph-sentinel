"""Server-composed alert titles (INTERFACES §6: `title` is composed from
summary_params, one clear template per typology).

Every accessor is .get() with a fallback: a malformed or Day-2
summary_params must degrade to a duller title, never to a 500. Unknown
typologies get a generic title so a new detection rule surfaces in the
console with zero API changes (ADR-008).
"""
import json


def _ghost_clinic(p: dict) -> str:
    return f"Ghost clinic pattern: {p.get('clinic_name', 'unnamed clinic')}"


def _credential_laundering(p: dict) -> str:
    # One rule, three sub-signals (DETECTION_SPEC §2) — the signal field
    # says which evidence this alert actually carries, so the title follows it.
    signal = p.get("signal", "")
    if signal == "shared_license":
        return (f"Credential laundering: licence {p.get('license_no', '?')} "
                f"held by {p.get('holder_count', '?')} doctors")
    has_revocation = "post_revocation_billing" in signal
    has_shopping = "jurisdiction_shopping" in signal
    if has_revocation and has_shopping:
        return "Credential laundering: post-revocation billing + jurisdiction shopping"
    if has_revocation:
        return (f"Credential laundering: {p.get('post_revocation_claims', '?')} "
                f"claims after licence revocation")
    if has_shopping:
        countries = p.get("claim_countries") or []
        return (f"Credential laundering: billing in {len(countries)} countries "
                f"outside the licence jurisdiction")
    return "Credential laundering alert"


def _kickback_ring(p: dict) -> str:
    return (f"Kickback ring: broker {p.get('broker_id', '?')} and "
            f"{p.get('clinic_name', 'unnamed clinic')}")


def _impossible_travel(p: dict) -> str:
    if p.get("passport_shared"):
        return (f"Impossible travel: one passport, "
                f"{p.get('identity_count', '?')} patient identities")
    return "Impossible travel: same-day claims in two countries"


def _template_cloning(p: dict) -> str:
    return (f"Template cloning: {p.get('cluster_size', '?')} near-identical "
            f"{p.get('procedure_name', 'procedure')} claims")


def _circular_payment(p: dict) -> str:
    return (f"Circular payment: ${p.get('amount_out_usd', 0):,.0f} returns "
            f"through {p.get('shell_count', '?')} shell account(s)")


_TEMPLATES = {
    "ghost_clinic": _ghost_clinic,
    "credential_laundering": _credential_laundering,
    "kickback_ring": _kickback_ring,
    "impossible_travel": _impossible_travel,
    "template_cloning": _template_cloning,
    "circular_payment": _circular_payment,
}


def parse_summary_params(raw) -> dict:
    """Alert.summary_params is stored as a JSON string (DATA_MODEL). Anything
    unparsable becomes {} — titles and fallback narration then degrade."""
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


def compose_title(typology: str, summary_params: dict) -> str:
    template = _TEMPLATES.get(typology)
    if template is None:
        return f"{typology.replace('_', ' ').capitalize()} alert"
    return template(summary_params)
