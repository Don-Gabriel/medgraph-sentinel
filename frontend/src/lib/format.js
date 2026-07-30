// Evidence-value formatting. summary_params keys are self-describing per
// rule (see api/titles.py / detection rule YAMLs), so formatting is keyed
// off the key name and the value's shape. Dates stay ISO 8601 — the
// project-wide convention (CLAUDE.md).

const nf = new Intl.NumberFormat("en-US");

export function labelize(key) {
  return key.replace(/_/g, " ");
}

// ---------------------------------------------------------------------------
// Enum-value dictionary: raw snake_case values from summary_params rendered
// as investigator English. Keyed BY PARAM KEY first so the same token can
// never be mistranslated in another key's context (e.g. a bare "none").
// Values verified against the live API across all four typologies and
// against api/narration/fallback.py + DETECTION_SPEC semantics — never
// invented (CLAUDE.md hard rule 2).
// ---------------------------------------------------------------------------

// Ghost-clinic feature tokens (strong_features array + features object keys).
const GHOST_FEATURES = {
  doctors: "too few doctors for the claim volume",
  footprint: "no physical footprint",
  inflow: "claims fed by a single broker",
  payout: "payouts landing in one account",
  single_visit: "patients who never return",
  address: "address shared with other entities",
};

const ENUM_LABELS = {
  // credential_laundering sub-signals
  signal: {
    shared_license: "Shared licence number",
    post_revocation_billing: "Billing after revocation",
    jurisdiction_shopping: "Practising outside issuing jurisdiction",
  },
  strong_features: GHOST_FEATURES,
  // kickback_ring / clinic property
  accreditation_status: {
    accredited: "accredited",
    provisional: "provisional accreditation only",
    none: "not accredited",
  },
};

function enumLabel(key, value) {
  return ENUM_LABELS[key]?.[value];
}

// impossible_travel packs claim pairs as {countries: [a,b], dates: [a,b]}.
function formatPair(p) {
  if (p && Array.isArray(p.countries) && Array.isArray(p.dates)) {
    return `${p.countries[0]} ${p.dates[0]} <> ${p.countries[1]} ${p.dates[1]}`;
  }
  return JSON.stringify(p);
}

export function formatValue(key, value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (Array.isArray(value)) {
    return value
      .map((v) =>
        typeof v === "object" ? formatPair(v) : enumLabel(key, v) ?? String(v),
      )
      .join(", ");
  }
  if (typeof value === "object") {
    // Plain objects (e.g. ghost_clinic `features` scores): readable pairs,
    // not JSON soup.
    return Object.entries(value)
      .map(([k, v]) => `${labelize(k)} ${formatValue(k, v)}`)
      .join(" · ");
  }
  if (typeof value === "string") {
    const mapped = enumLabel(key, value);
    if (mapped) return mapped;
  }
  if (typeof value === "number") {
    if (/_usd$/.test(key)) return `$${nf.format(Math.round(value))}`;
    if (/_pct$/.test(key)) return `${value}%`; // already on a 0–100 scale
    // Word-bounded: "registration" must not match "ratio".
    if (/(^|_)(share|ratio|softening)(_|$)/.test(key) && value >= 0 && value <= 1) {
      return `${(value * 100).toFixed(1)}%`; // fraction on a 0–1 scale
    }
    return nf.format(value);
  }
  return String(value);
}

// "2026-08-05T18:22:00Z" -> "2026-08-05" (ISO date, project convention).
export function formatDate(iso) {
  return typeof iso === "string" ? iso.slice(0, 10) : "—";
}

export function formatScore(score) {
  return Number(score).toFixed(1);
}

// ---------------------------------------------------------------------------
// One composed plain-English sentence per alert: WHAT FIRED, from the
// signal / strong_features keys (and the equivalent gate for the two rules
// that have neither). Shown at the top of the evidence panel so it opens
// with an explanation, not fields. Semantics mirror DETECTION_SPEC and the
// deterministic fallback narration — a summary of them, never new claims.
// Every value is optional-chained: malformed params degrade to null (no
// sentence), never to a crash.
// ---------------------------------------------------------------------------

const pct = (v) =>
  typeof v === "number" && v >= 0 && v <= 1 ? `${Math.round(v * 100)}%` : null;

function credentialSentence(p) {
  switch (p.signal) {
    case "shared_license":
      return `One licence number (${p.license_no ?? "unknown"}) sits behind ${p.holder_count ?? "several"} different doctor identities, ${p.actively_billing_holders ?? "some"} of them actively billing.`;
    case "post_revocation_billing":
      return `${p.post_revocation_claims ?? "Several"} claims were billed after this credential was revoked on ${p.revoked_on ?? "an unknown date"} — the first only ${p.days_from_revocation_to_first_claim ?? "?"} days later.`;
    case "jurisdiction_shopping":
      return `A licence issued in ${p.issued_in ?? "one jurisdiction"} is billing claims in ${(p.claim_countries ?? []).join(", ") || "other countries"} — never in its issuing jurisdiction.`;
    default:
      return null;
  }
}

function ghostSentence(p) {
  const feats = (p.strong_features ?? [])
    .map((f) => GHOST_FEATURES[f] ?? labelize(f))
    .join("; ");
  if (!feats) return null;
  return `${p.strong_features.length} of 6 ghost-clinic indicators fired strongly: ${feats}.`;
}

function travelSentence(p) {
  const n = p.impossible_pairs;
  const pairs =
    typeof n === "number"
      ? `${n} claim pair${n === 1 ? "" : "s"} ${n === 1 ? "places" : "place"}`
      : "at least one claim pair places";
  const gap = p.min_gap_days;
  const gapText =
    typeof gap === "number"
      ? gap === 0
        ? "on the same day"
        : `only ${gap} day${gap === 1 ? "" : "s"} apart`
      : "too close together to travel";
  if (p.passport_shared) {
    return `One passport backs ${p.identity_count ?? "several"} patient identities, and ${pairs} that document under treatment in two countries ${gapText}.`;
  }
  return `${pairs} this patient under treatment in two different countries ${gapText}.`;
}

function kickbackSentence(p) {
  const b = pct(p.broker_share);
  const c = pct(p.clinic_share);
  if (!b || !c) return null;
  const infra = [];
  if (p.stake_pct != null) infra.push(`a declared ${p.stake_pct}% stake`);
  if (p.transfers_to_broker_usd != null)
    infra.push(
      `$${nf.format(Math.round(p.transfers_to_broker_usd))} transferred clinic-to-broker against $${nf.format(Math.round(p.expected_commission_usd ?? 0))} expected commission`,
    );
  if (p.shell_paths) infra.push(`${p.shell_paths} shell-account path(s)`);
  if (p.shared_address) infra.push("a shared registered address");
  const tail = infra.length ? `, backed by ${infra.join(", ")}` : "";
  return `${b} of this broker's referrals and ${c} of the clinic's claims concentrate on each other${tail}.`;
}

const SENTENCES = {
  credential_laundering: credentialSentence,
  ghost_clinic: ghostSentence,
  impossible_travel: travelSentence,
  kickback_ring: kickbackSentence,
};

/** "What fired" in one sentence, or null when the typology is unknown
 *  (Day-2 rule) or the params don't carry the expected keys. */
export function summarizeEvidence(typology, summaryParams) {
  const compose = SENTENCES[typology];
  if (!compose) return null;
  try {
    return compose(summaryParams ?? {});
  } catch {
    return null;
  }
}
