import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { formatDate, formatScore, formatValue, labelize } from "../lib/format";
import SubgraphCanvas, { focusNode } from "./SubgraphCanvas";
import { EvidenceValues, NarrationBlock, ImplicatedList } from "./CaseFile";
import Disposition from "./Disposition";
import { StatusPill } from "./AlertQueue";

const SEVERITY_TEXT = {
  high: "text-heat-high",
  medium: "text-heat-med",
  low: "text-heat-low",
};

/**
 * Alert drill-down: case file (left) + evidence subgraph hero (right).
 * hops=1 by default (sub-second); hops=2 is an explicit async control
 * because the server takes 3-5 s there — this is our interpretation of
 * "click to expand one hop", since the API has no per-node expansion
 * endpoint (INTERFACES §6 offers only the whole-subgraph hops parameter).
 */
export default function AlertView({ id, onBack, onPatched }) {
  const [detail, setDetail] = useState(null);
  const [detailError, setDetailError] = useState(null);
  const [narration, setNarration] = useState(null);
  const [graph, setGraph] = useState(null); // {truncated, elements}
  const [graphError, setGraphError] = useState(null);
  const [graphLoading, setGraphLoading] = useState(true);
  const [hops, setHops] = useState(1);
  const [entity, setEntity] = useState(null); // {loading, data, error}
  const [saving, setSaving] = useState(false);
  const [patchError, setPatchError] = useState(null);
  const cyRef = useRef(null);

  // Case-file data: detail + narration, in parallel.
  useEffect(() => {
    let alive = true;
    setDetail(null);
    setDetailError(null);
    setNarration(null);
    setEntity(null);
    setPatchError(null);
    setHops(1);
    api
      .alert(id)
      .then((d) => alive && setDetail(d))
      .catch((e) => alive && setDetailError(e.message));
    api
      .narration(id)
      .then((n) => alive && setNarration(n))
      .catch(() => alive && setNarration(null));
    return () => {
      alive = false;
    };
  }, [id]);

  // Evidence subgraph; refetched when the hop radius changes. The old
  // graph stays visible under a loading veil during the 2-hop expansion.
  useEffect(() => {
    let alive = true;
    setGraphLoading(true);
    setGraphError(null);
    api
      .subgraph(id, hops)
      .then((g) => {
        if (!alive) return;
        setGraph(g);
        setGraphLoading(false);
      })
      .catch((e) => {
        if (!alive) return;
        setGraphError(e.message);
        setGraphLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [id, hops]);

  const handleReady = useCallback((cy) => {
    cyRef.current = cy;
  }, []);

  // Node click -> entity inspector via GET /entities/{id}.
  const handleNodeClick = useCallback((data) => {
    setEntity({ loading: true, id: data.id });
    api
      .entity(data.id)
      .then((e) => setEntity({ data: e }))
      .catch((err) => setEntity({ error: err.message, id: data.id }));
  }, []);

  const handleFocusEntity = (entityId) => {
    focusNode(cyRef.current, entityId);
    handleNodeClick({ id: entityId });
  };

  // PATCH with optimistic update + rollback (owner requirement 4).
  const applyPatch = async (body) => {
    const prev = detail;
    setDetail({ ...detail, ...body });
    setSaving(true);
    setPatchError(null);
    try {
      const updated = await api.patchAlert(id, body);
      setDetail(updated);
      onPatched(updated);
    } catch (e) {
      setDetail(prev); // roll back; the queue never saw the change
      setPatchError(`Not saved (${e.message}). The API may be unreachable — retry.`);
    } finally {
      setSaving(false);
    }
  };

  if (detailError) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-16 text-center">
        <p className="text-paper-mut">Could not load alert {id}: {detailError}</p>
        <button
          type="button"
          onClick={onBack}
          className="mt-4 rounded-sm border border-tracer/60 px-3 py-1.5 font-mono text-xs text-tracer"
        >
          Back to queue
        </button>
      </div>
    );
  }

  if (!detail) {
    return (
      <p className="px-6 py-16 text-center font-mono text-xs text-paper-dim">
        loading case file…
      </p>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {/* case header strip */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-ink-700 bg-ink-900 px-4 py-2.5 sm:px-6">
        <button
          type="button"
          onClick={onBack}
          className="rounded-sm border border-ink-700 px-2 py-1 font-mono text-[11px] text-paper-mut transition-colors hover:border-tracer/60 hover:text-tracer"
        >
          &larr; Queue
        </button>
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-sm font-semibold text-paper">{detail.title}</h2>
          <p className="font-mono text-[10px] text-paper-dim">
            {detail.id} · {detail.typology} · opened {formatDate(detail.created_at)}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-right">
            <span
              className={`block font-mono text-xl leading-none ${SEVERITY_TEXT[detail.severity] ?? "text-paper"}`}
            >
              {formatScore(detail.score)}
            </span>
            <span
              className={`block font-mono text-[9px] uppercase tracking-[0.14em] ${SEVERITY_TEXT[detail.severity]} opacity-70`}
            >
              {detail.severity} risk
            </span>
          </span>
          <StatusPill status={detail.status} />
        </div>
      </div>

      {/* body: graph hero + case file. Below lg it stacks (graph on top,
          fixed height) and scrolls as one column; at lg+ it splits into
          two panes that scroll internally (graph right, case file left via
          row-reverse — DOM keeps the graph first as the hero). */}
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto lg:flex-row-reverse lg:overflow-hidden">
        <main className="relative h-[48vh] min-h-[380px] shrink-0 bg-ink-950 lg:h-auto lg:min-h-0 lg:flex-1 lg:shrink">
          {graph && (
            <SubgraphCanvas
              elements={graph.elements}
              onNodeClick={handleNodeClick}
              onReady={handleReady}
            />
          )}

          {/* graph toolbar */}
          <div className="absolute left-3 right-3 top-3 flex flex-wrap items-center gap-2">
            {graph && (
              <span className="rounded border border-ink-700 bg-ink-900/90 px-2 py-1 font-mono text-[10px] text-paper-dim">
                {graph.elements.nodes.length} nodes · {graph.elements.edges.length} edges
                · {hops} hop{hops > 1 ? "s" : ""}
              </span>
            )}
            {graph?.truncated && (
              <span
                className="rounded border border-heat-high/60 bg-heat-high/10 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.1em] text-heat-high"
                title="The server trimmed lowest-relevance leaf nodes to stay under its 300-node cap"
              >
                trimmed by server cap
              </span>
            )}
            <span className="ml-auto flex gap-2">
              <button
                type="button"
                onClick={() => cyRef.current?.fit(undefined, 30)}
                className="rounded border border-ink-700 bg-ink-900/90 px-2 py-1 font-mono text-[10px] text-paper-mut transition-colors hover:border-tracer/60 hover:text-tracer"
              >
                Fit
              </button>
              {hops === 1 ? (
                <button
                  type="button"
                  disabled={graphLoading}
                  onClick={() => setHops(2)}
                  className="rounded border border-ink-700 bg-ink-900/90 px-2 py-1 font-mono text-[10px] text-paper-mut transition-colors hover:border-tracer/60 hover:text-tracer disabled:opacity-40"
                >
                  {graphLoading ? "Expanding…" : "Expand to 2 hops"}
                </button>
              ) : (
                <button
                  type="button"
                  disabled={graphLoading}
                  onClick={() => setHops(1)}
                  className="rounded border border-ink-700 bg-ink-900/90 px-2 py-1 font-mono text-[10px] text-paper-mut transition-colors hover:border-tracer/60 hover:text-tracer disabled:opacity-40"
                >
                  {graphLoading ? "Loading…" : "Back to 1 hop"}
                </button>
              )}
            </span>
          </div>

          {/* loading / error veils */}
          {graphLoading && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-ink-950/70">
              <p className="font-mono text-xs text-paper-mut">
                {graph ? `expanding to ${hops} hops — the server walks further out…`
                       : "laying out evidence graph…"}
              </p>
            </div>
          )}
          {graphError && !graphLoading && (
            <div className="absolute inset-0 flex items-center justify-center">
              <p className="font-mono text-xs text-heat-high">
                subgraph failed: {graphError}
              </p>
            </div>
          )}

          {entity && (
            <EntityInspector entity={entity} onClose={() => setEntity(null)} />
          )}
        </main>

        <aside className="w-full shrink-0 border-t border-ink-700 bg-ink-900 lg:w-[26rem] lg:overflow-y-auto lg:border-r lg:border-t-0">
          <EvidenceValues detail={detail} />
          <NarrationBlock narration={narration} />
          <ImplicatedList implicated={detail.implicated} onFocus={handleFocusEntity} />
          <Disposition
            detail={detail}
            saving={saving}
            error={patchError}
            onStatus={(status) => applyPatch({ status })}
            onSaveNote={(note) => applyPatch({ note })}
          />
        </aside>
      </div>
    </div>
  );
}

/** Side panel fed by GET /entities/{id} when a node is clicked. */
function EntityInspector({ entity, onClose }) {
  return (
    <div className="absolute bottom-3 right-3 top-14 z-20 w-72 overflow-y-auto rounded border border-ink-700 bg-ink-900/95 shadow-xl">
      <div className="flex items-start justify-between gap-2 border-b border-ink-700 px-4 py-3">
        <div className="min-w-0">
          <div className="font-mono text-[9px] uppercase tracking-[0.18em] text-paper-dim">
            Entity
          </div>
          {entity.loading ? (
            <div className="mt-1 font-mono text-xs text-paper-dim">loading…</div>
          ) : entity.error ? (
            <div className="mt-1 text-xs text-heat-high">
              {entity.id}: {entity.error}
            </div>
          ) : (
            <>
              <div className="mt-1 truncate text-sm font-semibold text-paper">
                {entity.data.label}
              </div>
              <div className="font-mono text-[10px] text-paper-mut">
                {entity.data.type} · {entity.data.id}
              </div>
            </>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close entity panel"
          className="rounded-sm px-1.5 py-0.5 font-mono text-xs text-paper-dim hover:bg-ink-800 hover:text-paper"
        >
          &times;
        </button>
      </div>
      {entity.data && (
        <dl className="space-y-1.5 px-4 py-3">
          <div className="flex justify-between gap-3">
            <dt className="text-xs text-paper-mut">connections</dt>
            <dd className="font-mono text-xs text-paper">{entity.data.degree}</dd>
          </div>
          {Object.entries(entity.data.props ?? {})
            .filter(([k]) => k !== "id")
            .map(([k, v]) => (
              <div key={k} className="flex justify-between gap-3">
                <dt className="text-xs text-paper-mut">{labelize(k)}</dt>
                <dd className="break-all text-right font-mono text-xs text-paper">
                  {formatValue(k, v)}
                </dd>
              </div>
            ))}
        </dl>
      )}
    </div>
  );
}
