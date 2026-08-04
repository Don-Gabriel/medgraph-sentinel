import { useEffect, useRef, useState } from "react";
import { api } from "../api";

/** AI-assist blocks (ADR-038): case-file report + case chat. Both are
 *  click-initiated (free-tier posture: no automatic calls), both label
 *  their source honestly, and both keep working offline — the report
 *  falls back to a deterministic template server-side, the chat says
 *  plainly that the live tier is down. */

const SOURCE_TAGS = {
  "gemini-live": { label: "live AI (Gemini)", cls: "border-heat-high/60 text-heat-high" },
  fallback: { label: "deterministic template", cls: "border-paper-dim/50 text-paper-mut" },
};

function SourceTag({ source }) {
  const tag = SOURCE_TAGS[source] ?? SOURCE_TAGS.fallback;
  return (
    <span
      className={`shrink-0 rounded-sm border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.1em] ${tag.cls}`}
    >
      {tag.label}
    </span>
  );
}

export function CaseReport({ alertId }) {
  const [state, setState] = useState({ status: "idle" }); // idle|loading|done|error

  useEffect(() => setState({ status: "idle" }), [alertId]);

  const load = () => {
    setState({ status: "loading" });
    api
      .report(alertId)
      .then((r) => setState({ status: "done", report: r }))
      .catch((e) => setState({ status: "error", error: e.message }));
  };

  return (
    <section className="border-t border-ink-700 px-5 py-4">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="font-mono text-[10px] uppercase tracking-[0.2em] text-paper-dim">
          Case-file report
        </h3>
        {state.status === "done" && <SourceTag source={state.report.source} />}
      </div>
      {state.status === "idle" && (
        <button
          onClick={load}
          className="mt-3 rounded-sm border border-tracer/50 px-3 py-1.5 font-mono text-xs text-tracer hover:bg-tracer/10"
        >
          Draft SIU report
        </button>
      )}
      {state.status === "loading" && (
        <p className="mt-3 font-mono text-xs text-paper-dim">
          drafting from the alert facts…
        </p>
      )}
      {state.status === "error" && (
        <p className="mt-3 font-mono text-xs text-heat-high">
          report failed: {state.error}
        </p>
      )}
      {state.status === "done" && (
        <>
          <pre className="mt-3 max-h-96 overflow-y-auto whitespace-pre-wrap font-serif text-[13px] leading-relaxed text-paper/90">
            {state.report.report}
          </pre>
          <button
            onClick={load}
            className="mt-2 font-mono text-[10px] text-paper-dim underline hover:text-paper"
          >
            regenerate
          </button>
        </>
      )}
    </section>
  );
}

export function CaseChat({ alertId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    setMessages([]);
    setInput("");
    setBusy(false);
  }, [alertId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "nearest" });
  }, [messages, busy]);

  const send = () => {
    const text = input.trim();
    if (!text || busy) return;
    const next = [...messages, { role: "user", text }];
    setMessages(next);
    setInput("");
    setBusy(true);
    api
      .chat(alertId, next.slice(-12)) // bounded context: free-tier tokens
      .then((r) =>
        setMessages((m) => [...m, { role: "assistant", text: r.reply, source: r.source }]),
      )
      .catch((e) =>
        setMessages((m) => [...m, { role: "assistant", text: `error: ${e.message}`, source: "fallback" }]),
      )
      .finally(() => setBusy(false));
  };

  return (
    <section className="border-t border-ink-700 px-5 py-4">
      <h3 className="font-mono text-[10px] uppercase tracking-[0.2em] text-paper-dim">
        Ask about this alert
      </h3>
      {messages.length > 0 && (
        <div className="mt-3 max-h-72 space-y-2 overflow-y-auto">
          {messages.map((m, i) => (
            <div key={i} className="text-[13px] leading-relaxed">
              <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-paper-dim">
                {m.role === "user" ? "you" : "analyst"}
              </span>
              <p
                className={
                  m.role === "user"
                    ? "text-paper"
                    : "font-serif text-paper/90"
                }
              >
                {m.text}
              </p>
            </div>
          ))}
          {busy && (
            <p className="font-mono text-xs text-paper-dim">thinking…</p>
          )}
          <div ref={endRef} />
        </div>
      )}
      <div className="mt-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="e.g. why is this scored high?"
          className="min-w-0 flex-1 rounded-sm border border-ink-700 bg-ink-950 px-2.5 py-1.5 font-mono text-xs text-paper placeholder:text-paper-dim/60 focus:border-tracer/60 focus:outline-none"
        />
        <button
          onClick={send}
          disabled={busy || !input.trim()}
          className="rounded-sm border border-tracer/50 px-3 py-1.5 font-mono text-xs text-tracer hover:bg-tracer/10 disabled:opacity-40"
        >
          ask
        </button>
      </div>
    </section>
  );
}
