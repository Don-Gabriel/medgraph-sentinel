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

// Sizing/contrast floor is set for a washed-out projector at 3 metres
// (demo constraint, DEMO_RUNBOOK): edges and minimum node sizes are
// deliberately heavier than a laptop screen needs.

// `dense` = large graphs (the 2-hop expansion): labels only on implicated
// nodes, otherwise 300 labelled nodes turn into text soup.
export function buildStylesheet(dense = false) {
  const base = [
    {
      selector: "node",
      style: {
        "background-color": FALLBACK.color,
        shape: FALLBACK.shape,
        width: 24,
        height: 24,
        "border-width": 1,
        "border-color": "#0A0D13",
        label: dense ? "" : "data(label)",
        color: "#6E7787", // neighbour labels stay quiet; implicated go bright
        "font-family": "IBM Plex Mono, monospace",
        "font-size": 9,
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
      style: { width: 14, height: 14, label: "" },
    },
    {
      selector: "node[?implicated]",
      style: {
        width: 40,
        height: 40,
        "border-width": 5,
        "border-color": EMBER,
        "underlay-color": EMBER,
        "underlay-opacity": 0.28,
        "underlay-padding": 9,
        label: "data(label)", // implicated nodes stay labelled even in dense mode
        color: "#E7E4DC",
        "font-size": 13,
        "font-weight": 600,
        "min-zoomed-font-size": 0, // never suppressed, whatever the zoom
        "text-outline-width": 3,
        "text-max-width": 150, // key actors show their full name
        "z-index": 10,
      },
    },
    // Implicated claims: still visibly flagged, but sized below the key
    // actors so a 60-claim fan doesn't drown the doctor who filed it.
    {
      selector: 'node[?implicated][type = "Claim"]',
      style: { width: 20, height: 20, label: "" },
    },
    // The typologies implicate hub PAIRS that cose keeps adjacent (clinic +
    // broker, doctor + credential): the org/document label goes ABOVE its
    // node so two always-on labels can never stack in the shared hub.
    // Draw order (a node paints its own label): implicated claims 10 <
    // top-labelled orgs 11 < bottom-labelled actors 12 — so an actor's
    // label paints OVER an adjacent org node instead of hiding behind it
    // (the 3px dark outline keeps it readable on any fill).
    {
      selector: 'node[?implicated][type != "Claim"]',
      style: { "z-index": 12 },
    },
    {
      selector:
        'node[?implicated][type = "Clinic"], node[?implicated][type = "Credential"]',
      style: { "text-valign": "top", "text-margin-y": -6, "z-index": 11 },
    },
    // Third label row: money/place hubs drop their label a step lower, so
    // when cose lands broker + account side by side their two bottom
    // labels sit on different lines instead of one overlapping line.
    {
      selector:
        'node[?implicated][type = "PaymentAccount"], node[?implicated][type = "Address"]',
      style: { "text-margin-y": 18 },
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
        width: 2,
        "line-color": "#47536C",
        "line-opacity": 0.9,
        "curve-style": "haystack",
        "haystack-radius": 0.2,
      },
    },
  ];

  return [...base, ...perType, ...overrides];
}

// Post-layout pass: the implicated key actors (clinic + broker + account
// share an edge to EVERY claim in the fan, so their cose equilibria are
// nearly the same point) can land coincident, stacking their always-on
// labels. Push any pair closer than minDist apart along their own axis,
// a few relaxation passes, claims and neighbours untouched. Deterministic
// given positions, ~O(actors^2) with actors <= a dozen.
// minDist 140 is a tuned compromise, not a guess: below ~120 the account
// label still lands under the broker node; above ~170 the pushed-apart
// actors widen the graph's bounding box enough that the follow-up fit()
// zooms everything down and costs more legibility than it buys.
export function spreadImplicatedActors(cy, minDist = 140) {
  const actors = cy.nodes('node[?implicated][type != "Claim"]').toArray();
  for (let pass = 0; pass < 8; pass++) {
    let moved = false;
    for (let i = 0; i < actors.length; i++) {
      for (let j = i + 1; j < actors.length; j++) {
        const a = actors[i].position();
        const b = actors[j].position();
        let dx = b.x - a.x;
        let dy = b.y - a.y;
        let d = Math.hypot(dx, dy);
        if (d >= minDist) continue;
        if (d < 1) {
          dx = 1; dy = 0; d = 1; // coincident: separate horizontally
        }
        const push = (minDist - d) / 2 / d;
        actors[i].position({ x: a.x - dx * push, y: a.y - dy * push });
        actors[j].position({ x: b.x + dx * push, y: b.y + dy * push });
        moved = true;
      }
    }
    if (!moved) break;
  }
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
  // Spacing re-tuned 2026-07-30 for the projector-legibility node sizes
  // (24px base / 40px implicated): the same relative geometry as the OQ #6
  // verdict, scaled so adjacent implicated hubs' labels stop colliding.
  idealEdgeLength: 64, // default 32: give hub clusters breathing room
  nodeRepulsion: 9216, // default 2048: push unconnected nodes apart harder
  nodeOverlap: 24, // default 4: hub pairs (broker+clinic) must never stack
  edgeElasticity: 64, // default 32 (divisor): weaker springs, repulsion wins
};
