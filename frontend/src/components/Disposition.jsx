import { useEffect, useState } from "react";
import { SectionLabel } from "./CaseFile";

const NOTE_MAX = 2000; // PATCH contract: note <= 2000 chars (INTERFACES §6)

/**
 * Status + note controls, wired to PATCH /alerts/{id} by AlertView with
 * optimistic updates. This component only renders state and collects input.
 */
export default function Disposition({ detail, onStatus, onSaveNote, saving, error }) {
  const [draft, setDraft] = useState(detail.note ?? "");

  // Re-sync the draft when a different alert (or server response) loads.
  useEffect(() => {
    setDraft(detail.note ?? "");
  }, [detail.id, detail.note]);

  const overLimit = draft.length > NOTE_MAX;
  const dirty = draft !== (detail.note ?? "");
  const { status } = detail;

  const btn =
    "rounded-sm border px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.1em] transition-colors disabled:opacity-40";

  return (
    <section className="border-t border-ink-700 px-5 py-4">
      <SectionLabel>Disposition</SectionLabel>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {status !== "reviewed" && (
          <button
            type="button"
            disabled={saving}
            onClick={() => onStatus("reviewed")}
            className={`${btn} border-tracer/60 text-tracer hover:bg-tracer/10`}
          >
            Mark reviewed
          </button>
        )}
        {status !== "dismissed" && (
          <button
            type="button"
            disabled={saving}
            onClick={() => onStatus("dismissed")}
            className={`${btn} border-paper-dim/50 text-paper-mut hover:bg-ink-800`}
          >
            Dismiss
          </button>
        )}
        {status !== "new" && (
          <button
            type="button"
            disabled={saving}
            onClick={() => onStatus("new")}
            className={`${btn} border-paper-dim/50 text-paper-mut hover:bg-ink-800`}
          >
            Reopen
          </button>
        )}
      </div>

      <div className="mt-3">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={3}
          placeholder="Investigator note — what was checked, what was found."
          className="w-full resize-y rounded-sm border border-ink-700 bg-ink-850 px-2.5 py-2 text-xs text-paper placeholder:text-paper-dim"
        />
        <div className="mt-1 flex items-center justify-between">
          <span
            className={`font-mono text-[10px] ${overLimit ? "text-heat-high" : "text-paper-dim"}`}
          >
            {draft.length}/{NOTE_MAX}
          </span>
          <button
            type="button"
            disabled={saving || overLimit || !dirty}
            onClick={() => onSaveNote(draft)}
            className={`${btn} border-tracer/60 text-tracer hover:bg-tracer/10`}
          >
            {saving ? "Saving…" : "Save note"}
          </button>
        </div>
      </div>

      {error && <p className="mt-2 text-xs text-heat-high">{error}</p>}
    </section>
  );
}
