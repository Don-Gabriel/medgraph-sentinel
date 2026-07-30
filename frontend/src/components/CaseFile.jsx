import { useState } from "react";
import { formatValue, labelize } from "../lib/format";
import { typeStyle } from "../lib/graphStyle";

// The left column of the alert view: the case file. Section eyebrows are
// mono smallcaps because they encode the real structure of an
// investigation record — evidence, narration, entities, disposition.

export function SectionLabel({ children }) {
  return (
    <h3 className="font-mono text-[10px] uppercase tracking-[0.2em] text-paper-dim">
      {children}
    </h3>
  );
}

/** Why this alert fired: rule + version, then summary_params as labelled
 *  evidence values (formatted per key shape — see lib/format.js). */
export function EvidenceValues({ detail }) {
  const params = detail.summary_params ?? {};
  const entries = Object.entries(params);
  return (
    <section className="border-t border-ink-700 px-5 py-4">
      <div className="flex items-baseline justify-between">
        <SectionLabel>Evidence</SectionLabel>
        <span className="font-mono text-[10px] text-paper-dim">
          rule {detail.typology} v{detail.rule_version}
        </span>
      </div>
      <dl className="mt-3 space-y-1.5">
        {entries.map(([k, v]) => (
          <div key={k} className="flex items-baseline justify-between gap-4">
            <dt className="text-xs text-paper-mut">{labelize(k)}</dt>
            <dd className="text-right font-mono text-xs text-paper">
              {formatValue(k, v)}
            </dd>
          </div>
        ))}
        {entries.length === 0 && (
          <p className="text-xs text-paper-dim">
            This rule attached no summary parameters.
          </p>
        )}
      </dl>
    </section>
  );
}

const NARRATION_SOURCES = {
  "claude-cached": { label: "cached AI narration", cls: "border-tracer/60 text-tracer" },
  "claude-live": { label: "live AI narration", cls: "border-tracer/60 text-tracer" },
  fallback: { label: "deterministic fallback", cls: "border-paper-dim/50 text-paper-mut" },
};

/** Plain-English explanation, set in serif — the analyst's brief. The
 *  source tag is honest about whether Claude or the template wrote it. */
export function NarrationBlock({ narration }) {
  return (
    <section className="border-t border-ink-700 px-5 py-4">
      <div className="flex items-baseline justify-between gap-3">
        <SectionLabel>Analyst narration</SectionLabel>
        {narration && (
          <span
            className={`shrink-0 rounded-sm border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.1em] ${
              (NARRATION_SOURCES[narration.source] ?? NARRATION_SOURCES.fallback).cls
            }`}
          >
            {(NARRATION_SOURCES[narration.source] ?? NARRATION_SOURCES.fallback).label}
          </span>
        )}
      </div>
      {narration ? (
        <p className="mt-3 font-serif text-[14px] leading-relaxed text-paper/90">
          {narration.text}
        </p>
      ) : (
        <p className="mt-3 text-xs text-paper-dim">Narration unavailable.</p>
      )}
    </section>
  );
}

/** Implicated entities, grouped by role. Small groups (the doctor, the
 *  credential) surface first; the large claim fan stays collapsed. */
export function ImplicatedList({ implicated, onFocus }) {
  const [expanded, setExpanded] = useState(() => new Set());

  const groups = new Map();
  for (const e of implicated ?? []) {
    const role = e.role ?? "unspecified";
    if (!groups.has(role)) groups.set(role, []);
    groups.get(role).push(e);
  }
  const ordered = [...groups.entries()].sort((a, b) => a[1].length - b[1].length);

  const toggle = (role) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(role)) next.delete(role);
      else next.add(role);
      return next;
    });

  return (
    <section className="border-t border-ink-700 px-5 py-4">
      <div className="flex items-baseline justify-between">
        <SectionLabel>Implicated entities</SectionLabel>
        <span className="font-mono text-[10px] text-paper-dim">
          {implicated?.length ?? 0} total
        </span>
      </div>
      <div className="mt-3 space-y-3">
        {ordered.map(([role, members]) => {
          const open = expanded.has(role);
          const shown = open ? members : members.slice(0, 6);
          return (
            <div key={role}>
              <div className="mb-1 flex items-baseline gap-2">
                <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-heat-high/80">
                  {labelize(role)}
                </span>
                <span className="font-mono text-[10px] text-paper-dim">
                  x{members.length}
                </span>
              </div>
              <ul className="space-y-px">
                {shown.map((e) => (
                  <li key={e.id}>
                    <button
                      type="button"
                      onClick={() => onFocus(e.id)}
                      title="Locate in the evidence graph"
                      className="flex w-full items-center gap-2 rounded-sm px-1.5 py-1 text-left transition-colors hover:bg-ink-800"
                    >
                      <span
                        className="h-2 w-2 shrink-0 rounded-full"
                        style={{ background: typeStyle(e.type).color }}
                      />
                      <span className="truncate text-xs text-paper">{e.label}</span>
                      <span className="ml-auto shrink-0 font-mono text-[10px] text-paper-dim">
                        {e.type}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
              {members.length > 6 && (
                <button
                  type="button"
                  onClick={() => toggle(role)}
                  className="mt-1 px-1.5 font-mono text-[10px] text-tracer hover:underline"
                >
                  {open ? "collapse" : `show all ${members.length}`}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
