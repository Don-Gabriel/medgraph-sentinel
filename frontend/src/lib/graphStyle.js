// Cytoscape styling, keyed off data.type / data.implicated / data.role —
// exactly the fields the contract says styling may key off (INTERFACES §7).
//
// Shape groups carry meaning: people are ellipses, organisations are
// round-rectangles, money is a hexagon, documents are tags, places are
// triangles, and claims are the small dim dots that form the "fan" —
// numerous by design, so they stay quiet until implicated.
export const NODE_TYPES = {
  Patient: { color: "#7FB0E8", shape: "ellipse" },
  Doctor: { color: "#59C2B0", shape: "ellipse" },
  Broker: { color: "#C583C9", shape: "diamond" },
  Clinic: { color: "#8F8AE8", shape: "round-rectangle" },
  Insurer: { color: "#6E87C9", shape: "round-rectangle" },
  Claim: { color: "#55617A", shape: "ellipse" },
  Credential: { color: "#D9B96A", shape: "tag" },
  PaymentAccount: { color: "#79C98A", shape: "hexagon" },
  Device: { color: "#58AFC9", shape: "rectangle" },
  Address: { color: "#B08D6E", shape: "triangle" },
  Procedure: { color: "#9A86B8", shape: "barrel" },
  Country: { color: "#7A8699", shape: "octagon" },
};

const FALLBACK = { color: "#6B7280", shape: "ellipse" };

export function typeStyle(type) {
  return NODE_TYPES[type] ?? FALLBACK;
}

// Implicated nodes must be unmistakable vs neighbours by size AND colour
// AND border (owner requirement — never colour alone): ~1.7x size, thick
// ember border, ember halo (underlay), brighter label.
const EMBER = "#FF6A3D";

// `dense` = large graphs (the 2-hop expansion): labels only on implicated
// nodes, otherwise 300 labelled nodes turn into text soup.
export function buildStylesheet(dense = false) {
  const base = [
    {
      selector: "node",
      style: {
        "background-color": FALLBACK.color,
        shape: FALLBACK.shape,
        width: 18,
        height: 18,
        "border-width": 1,
        "border-color": "#0A0D13",
        label: dense ? "" : "data(label)",
        color: "#6E7787", // neighbour labels stay quiet; implicated go bright
        "font-family": "IBM Plex Mono, monospace",
        "font-size": 8,
        "min-zoomed-font-size": 7,
        "text-valign": "bottom",
        "text-margin-y": 4,
        "text-wrap": "ellipsis",
        "text-max-width": 90,
        // labels must survive crossing edges and neighbour fans
        "text-outline-color": "#0A0D13",
        "text-outline-width": 2,
      },
    },
  ];

  const perType = Object.entries(NODE_TYPES).map(([type, s]) => ({
    selector: `node[type = "${type}"]`,
    style: { "background-color": s.color, shape: s.shape },
  }));

  const overrides = [
    // Claims are the numerous fan: small, unlabelled (tooltip carries it).
    {
      selector: 'node[type = "Claim"]',
      style: { width: 10, height: 10, label: "" },
    },
    {
      selector: "node[?implicated]",
      style: {
        width: 30,
        height: 30,
        "border-width": 3,
        "border-color": EMBER,
        "underlay-color": EMBER,
        "underlay-opacity": 0.16,
        "underlay-padding": 7,
        label: "data(label)", // implicated nodes stay labelled even in dense mode
        color: "#E7E4DC",
        "font-size": 10,
        "font-weight": 500,
        "z-index": 10,
      },
    },
    // Implicated claims: still visibly flagged, but sized below the key
    // actors so a 60-claim fan doesn't drown the doctor who filed it.
    {
      selector: 'node[?implicated][type = "Claim"]',
      style: { width: 15, height: 15, label: "" },
    },
    {
      selector: "node:selected",
      style: {
        "overlay-color": "#57C4B8",
        "overlay-opacity": 0.2,
        "overlay-padding": 6,
      },
    },
    {
      selector: "edge",
      style: {
        width: 1,
        "line-color": "#2A3242",
        "curve-style": "haystack",
        "haystack-radius": 0.2,
      },
    },
  ];

  return [...base, ...perType, ...overrides];
}

// OQ #6: built-in cose first; extension only if unreadable. Verdict: cose
// is readable for 100-300 node evidence subgraphs once spacing is tuned —
// no extension needed (finding recorded in frontend/README.md). The two
// spacing knobs below stop densely-connected hub pairs (broker + clinic)
// from landing on top of each other. animate:false = layout runs once,
// then the graph is still.
export const COSE_LAYOUT = {
  name: "cose",
  animate: false,
  padding: 30,
  fit: true,
  idealEdgeLength: 48, // default 32: give hub clusters breathing room
  nodeRepulsion: 6144, // default 2048: push unconnected nodes apart harder
  nodeOverlap: 24, // default 4: hub pairs (broker+clinic) must never stack
  edgeElasticity: 64, // default 32 (divisor): weaker springs, repulsion wins
};
