import { useEffect, useMemo, useRef, useState } from "react";
import cytoscape from "cytoscape";
import {
  buildStylesheet,
  typeStyle,
  COSE_LAYOUT,
  spreadImplicatedActors,
} from "../lib/graphStyle";
import { formatValue, labelize } from "../lib/format";

// Props shown in the hover tooltip, in priority order; the first four
// present on the node win. Keys come from the generator CSV columns.
const TOOLTIP_KEYS = [
  "amount_usd",
  "status",
  "specialty",
  "license_no",
  "bed_count",
  "accreditation_status",
  "bank_name",
  "procedure_date",
  "submission_date",
  "revocation_date",
  "opened_date",
  "registration_date",
  "agency_name",
  "device_type",
  "category",
  "code",
];

const prefersReducedMotion = () =>
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * The evidence subgraph — renders the API's Cytoscape `elements` verbatim
 * (INTERFACES §7). Owns the cy instance, the hover tooltip and the legend;
 * everything else (entity panel, hop controls) lives in AlertView.
 */
export default function SubgraphCanvas({ elements, onNodeClick, onReady }) {
  const containerRef = useRef(null);
  const [tip, setTip] = useState(null); // {x, y, data}

  useEffect(() => {
    if (!elements) return undefined;
    setTip(null); // a rebuilt graph invalidates any hover tooltip
    // Dense mode = labels only on implicated nodes. Threshold 60, not 150:
    // the ghost-clinic evidence view is 117 nodes, so at 150 it labelled
    // every neighbouring patient and doctor — thirty-odd names competing
    // with the four that carry the finding (clinic, broker, account,
    // address). The 19-node impossible-travel view sits well under 60 and
    // keeps its neighbour labels, where they still help.
    const dense = elements.nodes.length > 60;
    const cy = cytoscape({
      container: containerRef.current,
      elements, // verbatim from GET /alerts/{id}/subgraph
      style: buildStylesheet(dense),
      layout: { ...COSE_LAYOUT },
    });

    // cose can drop the co-hubbed key actors on one spot (see
    // spreadImplicatedActors); separate them once the layout settles, then
    // re-fit so nothing sits outside the frame.
    cy.one("layoutstop", () => {
      spreadImplicatedActors(cy);
      cy.fit(undefined, 30);
    });

    cy.on("tap", "node", (evt) => {
      setTip(null);
      onNodeClick?.(evt.target.data());
    });
    cy.on("mouseover", "node", (evt) => {
      containerRef.current.style.cursor = "pointer";
      const pos = evt.target.renderedPosition();
      setTip({ x: pos.x, y: pos.y, data: evt.target.data() });
    });
    cy.on("mouseout", "node", () => {
      if (containerRef.current) containerRef.current.style.cursor = "default";
      setTip(null);
    });
    // Any viewport change invalidates the tooltip's pinned position.
    cy.on("pan zoom", () => setTip(null));
    cy.on("drag", "node", () => setTip(null));

    onReady?.(cy);
    return () => cy.destroy();
  }, [elements, onNodeClick, onReady]);

  const legendTypes = useMemo(() => {
    if (!elements?.nodes) return [];
    const seen = new Set(elements.nodes.map((n) => n.data.type));
    return [...seen].sort();
  }, [elements]);

  return (
    <div className="relative h-full w-full overflow-hidden">
      <div ref={containerRef} className="h-full w-full" />

      {tip && <NodeTooltip tip={tip} />}

      {legendTypes.length > 0 && (
        <div className="pointer-events-none absolute bottom-3 left-3 rounded border border-ink-700 bg-ink-900/90 px-3 py-2">
          <div className="mb-1 font-mono text-[9px] uppercase tracking-[0.18em] text-paper-dim">
            Legend
          </div>
          <ul className="grid grid-cols-2 gap-x-4 gap-y-0.5 sm:grid-cols-1">
            {legendTypes.map((t) => (
              <li key={t} className="flex items-center gap-1.5">
                <span
                  className="inline-block h-2 w-2 rounded-full"
                  style={{ background: typeStyle(t).color }}
                />
                <span className="font-mono text-[10px] text-paper-mut">{t}</span>
              </li>
            ))}
            <li className="mt-1 flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-full border-2 border-heat-high" />
              <span className="font-mono text-[10px] text-heat-high">
                implicated
              </span>
            </li>
          </ul>
        </div>
      )}
    </div>
  );
}

function NodeTooltip({ tip }) {
  const { data } = tip;
  const props = data.props ?? {};
  const rows = TOOLTIP_KEYS.filter((k) => props[k] !== undefined).slice(0, 4);
  return (
    <div
      className="pointer-events-none absolute z-20 max-w-[240px] rounded border border-ink-700 bg-ink-900/95 px-3 py-2 shadow-lg"
      style={{ left: tip.x + 14, top: tip.y + 10 }}
    >
      <div className="text-xs font-semibold text-paper">{data.label}</div>
      <div className="mt-0.5 font-mono text-[10px] text-paper-mut">
        {data.type}
        {data.implicated && (
          <span className="ml-2 text-heat-high">
            implicated{data.role ? ` · ${data.role}` : ""}
          </span>
        )}
      </div>
      {rows.length > 0 && (
        <dl className="mt-1.5 space-y-0.5 border-t border-ink-700 pt-1.5">
          {rows.map((k) => (
            <div key={k} className="flex justify-between gap-3">
              <dt className="font-mono text-[10px] text-paper-dim">
                {labelize(k)}
              </dt>
              <dd className="font-mono text-[10px] text-paper-mut">
                {formatValue(k, props[k])}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

// Helper used by AlertView when an implicated row is clicked: select the
// node and glide the viewport to it.
export function focusNode(cy, id) {
  if (!cy) return;
  const node = cy.$id(id);
  if (node.empty()) return;
  cy.elements().unselect();
  node.select();
  cy.animate(
    { center: { eles: node }, zoom: Math.max(cy.zoom(), 1.1) },
    { duration: prefersReducedMotion() ? 0 : 350 },
  );
}
