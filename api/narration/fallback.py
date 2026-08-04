"""Deterministic fallback narration — one template per typology, a pure
function of summary_params (INTERFACES §8, ADR-010).

Served whenever the committed Claude cache has no usable entry for an
alert. Tone rule: state the measured evidence and why it matches the
typology, then a next step — never assert guilt (these are leads for an
investigator, and honest economies produce look-alikes; the FP modes in
DETECTION_SPEC are real).

Every value is .get() with a fallback so malformed params degrade to
vaguer prose, never to a 500 — the demo must not know how to crash.
"""


def _pct(value, fallback="an unknown share of") -> str:
    try:
        return f"{float(value):.0%}"
    except (TypeError, ValueError):
        return fallback


def _ghost_clinic(p: dict) -> str:
    return (
        f"{p.get('clinic_name', 'This clinic')} has filed "
        f"{p.get('claim_count', 'a large number of')} claims with "
        f"{p.get('bed_count', 'few')} beds and "
        f"{p.get('registration_age_years', 'few')} years of operating history. "
        f"{_pct(p.get('inflow_share'))} of its claims arrive through a single "
        f"broker and {_pct(p.get('payout_share'))} of payouts land in one "
        f"account, with {p.get('distinct_doctors', 'few')} doctors covering the "
        f"entire caseload. Billing volume without physical footprint, fed and "
        f"paid through single channels, is the ghost-clinic pattern. Next step: "
        f"verify the premises, staffing and accreditation trail before "
        f"approving further claims."
    )


def _credential_laundering(p: dict) -> str:
    signal = p.get("signal", "")
    if signal == "shared_license":
        countries = ", ".join(p.get("issuing_countries") or []) or "unknown countries"
        return (
            f"Licence number {p.get('license_no', 'unknown')} appears on "
            f"credentials held by {p.get('holder_count', 'several')} different "
            f"doctors ({p.get('actively_billing_holders', 'some')} actively "
            f"billing), issued in {countries}. One licence number backing "
            f"several practising identities is the credential-laundering "
            f"signature; genuine format collisions exist but do not span "
            f"countries or many holders. Next step: ask the issuing body which "
            f"holder, if any, is the legitimate one."
        )
    parts = []
    if "post_revocation_billing" in signal:
        parts.append(
            f"this doctor billed {p.get('post_revocation_claims', 'several')} "
            f"claims after credential {p.get('revoked_credential', 'unknown')} "
            f"was revoked on {p.get('revoked_on', 'an unknown date')} (first "
            f"claim {p.get('days_from_revocation_to_first_claim', '?')} days "
            f"after revocation)"
        )
    if "jurisdiction_shopping" in signal:
        countries = ", ".join(p.get("claim_countries") or []) or "several countries"
        parts.append(
            f"this doctor holds credential {p.get('shopped_credential', 'unknown')} "
            f"issued in {p.get('issued_in', 'one jurisdiction')} yet bills "
            f"claims in {countries}, none of them the issuing jurisdiction"
        )
    if not parts:
        parts.append("this doctor's credential activity does not match their billing")
    body = "; furthermore, ".join(parts)
    return (
        f"Working on a dead or displaced licence: {body}. Clinics do keep "
        f"retired doctors on rosters, so volume and recency matter more than "
        f"existence. Next step: confirm the doctor's current licence status "
        f"with the registry and match it against the claim dates."
    )


def _kickback_ring(p: dict) -> str:
    evidence = []
    if p.get("stake_pct") is not None:
        evidence.append(f"the broker holds a {p['stake_pct']}% stake in the clinic")
    if p.get("transfers_to_broker_usd") is not None:
        evidence.append(
            f"clinic-to-broker transfers of ${p['transfers_to_broker_usd']:,.0f} "
            f"against ${p.get('expected_commission_usd', 0):,.0f} of expected "
            f"commission"
        )
    if p.get("shell_paths"):
        evidence.append(
            f"{p['shell_paths']} money path(s) routed through unowned shell accounts"
        )
    if p.get("shared_address"):
        evidence.append("a shared registered address")
    if p.get("common_accounts"):
        evidence.append("payment accounts owned by both parties")
    shared = ("Shared infrastructure: " + "; ".join(evidence) + ". ") if evidence else ""
    return (
        f"Broker {p.get('broker_id', 'unknown')} routed "
        f"{p.get('pair_claims', 'many')} claims worth "
        f"${p.get('pair_amount_usd', 0):,.0f} to "
        f"{p.get('clinic_name', 'one clinic')} — "
        f"{_pct(p.get('broker_share'))} of the broker's referrals and "
        f"{_pct(p.get('clinic_share'))} of the clinic's inflow. {shared}"
        f"Referral concentration alone can be an honest exclusive partnership; "
        f"concentration plus shared money infrastructure is the kickback "
        f"pattern. Next step: review the transfer trail and any undeclared "
        f"ownership between the two parties."
    )


def _impossible_travel(p: dict) -> str:
    pairs = p.get("pairs") or []
    example = ""
    if pairs:
        first = pairs[0]
        countries = first.get("countries", ["?", "?"])
        dates = first.get("dates", ["?", "?"])
        example = (f" For example, claims place them in {countries[0]} on "
                   f"{dates[0]} and in {countries[1]} on {dates[1]}.")
    if p.get("passport_shared"):
        return (
            f"One passport is shared by {p.get('identity_count', 'several')} "
            f"patient identities, and {p.get('impossible_pairs', 'several')} "
            f"claim pair(s) put that document under treatment in two countries "
            f"{p.get('min_gap_days', 0)} day(s) apart — travel that is not "
            f"physically possible.{example} A document cannot be in two "
            f"clinics at once; identities recycled across borders are the "
            f"signal here. Next step: pull the passport-linked patient records "
            f"and compare the identity details behind each claim."
        )
    return (
        f"This patient has {p.get('impossible_pairs', 'at least one')} claim "
        f"pair(s) showing same-day treatment in two different countries."
        f"{example} Date-entry artifacts do occur, so a single pair on one "
        f"identity is a lead, not a verdict. Next step: check the underlying "
        f"treatment records for which claim carries the wrong date — or "
        f"whether both are real and someone else used this identity."
    )


def _template_cloning(p: dict) -> str:
    devices = p.get("shared_devices", 0)
    device_clause = (
        f"and {devices} submission device(s) are shared across those "
        f"patients — unrelated medical tourists do not file from the same "
        f"computer " if devices else ""
    )
    return (
        f"{p.get('cluster_size', 'Several')} claims for "
        f"{p.get('procedure_name', 'the same procedure')} are near-identical "
        f"copies of one claim package: the same {p.get('line_item_count', '?')} "
        f"line items, narratives within {p.get('max_hamming', '?')} bits of "
        f"each other, and amounts inside a {p.get('amount_band_pct', '?')}% "
        f"band. They were filed for {p.get('distinct_patients', '?')} "
        f"different patients across {p.get('distinct_insurers', '?')} "
        f"insurer(s) {device_clause}— a template resubmitted with names "
        f"swapped, the claim-mill pattern. Genuinely standardized packages "
        f"do produce similar claims within one clinic and one insurer, "
        f"which is why cross-insurer spread and shared devices drive this "
        f"score. Next step: request the underlying treatment records for "
        f"two claims in the cluster and compare them line by line."
    )


_TEMPLATES = {
    "ghost_clinic": _ghost_clinic,
    "credential_laundering": _credential_laundering,
    "kickback_ring": _kickback_ring,
    "impossible_travel": _impossible_travel,
    "template_cloning": _template_cloning,
}


def fallback_text(typology: str, summary_params: dict) -> str:
    template = _TEMPLATES.get(typology)
    if template is None:
        # Day-2 rule with no template yet: show the evidence verbatim rather
        # than nothing (ADR-008 extensibility — the console still works).
        evidence = ", ".join(
            f"{k}={v}" for k, v in sorted(summary_params.items())
            if isinstance(v, (str, int, float, bool))
        )
        name = typology.replace("_", " ")
        return (f"Alert raised by rule '{name}'. Evidence: "
                f"{evidence or 'see summary parameters'}. Review the "
                f"implicated entities and the evidence subgraph.")
    try:
        return template(summary_params)
    except Exception:  # malformed params: degrade, never 500 (ADR-010 spirit)
        return (f"Alert raised by rule '{typology.replace('_', ' ')}'. "
                f"Evidence values could not be rendered; review the "
                f"implicated entities and the evidence subgraph.")
