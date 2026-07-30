# Pitch — Rehearsal Kit

**This is a script, not an essay.** Read it standing up, out loud, with a
timer. Version 3 (2026-07-30), locked to the real console and the real
numbers. One presenter: J Don Gabriel, start to finish.

Contents: [60-second version](#the-60-second-version) ·
[3-minute version](#the-3-minute-version) ·
[10-minute script](#the-10-minute-pitch--runnable-script) ·
[self-scoring rubric](#self-scoring-rubric-no-audience-needed) ·
[15 questions](#the-15-questions-ordered-by-likelihood) ·
[held-out numbers](#the-held-out-numbers--exact-say-them-this-way)

---

## The numbers, memorised (never guess these on stage)

| thing | number |
|---|---|
| graph | **52,071 nodes · 199,349 relationships** |
| alerts | **81**, precomputed and committed |
| typologies | **4 shipping** (ghost clinic, credential laundering, kickback ring, impossible travel), 2 fully specified as next-build |
| boot | seed loads in **~21 s**; whole stack healthy in **~48 s**, fully offline |
| detection runtime | **3–9 s** for all four rules over the whole graph |
| honest-economy calibration | **zero medium-or-high alerts** on every rule |
| dev set | planted cells **3/3** ghost and **3/3** credential, all at `high`; impossible-travel groups **3/3** at `high`; kickback precision **1.0**, broker recall **6/13** |
| held-out | 5 scenarios · **8 legs expected · 5 detected · 3 missed · 2 root causes** |
| betweenness | **131.6 s** and the *worst* discriminator (precision@13 **0.077** vs **0.385** for a one-line concentration feature) |

---

## The 60-second version

*(Hallway. Someone asks "what did you build?")*

> "Medical tourism fraud. When someone flies abroad for surgery, five
> different organisations hold a piece of the record — their insurer, the
> clinic, the broker who arranged it, two countries' health systems — and
> none of them sees the whole chain. Organised fraud is built for exactly
> that gap: every individual record looks clean, and the pattern only
> exists in how records connect.
>
> So I built the connected version. Fifty thousand entities in a Neo4j
> graph, four fraud typologies detected with graph algorithms and targeted
> Cypher, and an investigator console that shows you the specific subgraph
> of evidence and explains it in plain English.
>
> The part I'd want you to poke at: I wrote five test scenarios and
> published their hashes *before* I'd written a single detection query, so
> the git history proves I didn't write the tests to fit the answers. It
> caught five of eight, and I can tell you exactly why it missed three."

**Timing target: 55–65 s.** If they're still listening, go to the 3-minute
version. Do not accelerate — the last paragraph is the one that gets you a
follow-up question.

---

## The 3-minute version

*(Recruiter, or a judge between rounds. Add to the 60-second version:)*

**The insight (30 s).** "Today's fraud detection is per-claim: one insurer
scores one claim against its own history. That catches a bad claim. It
structurally cannot catch a bad *network* — one licence number behind four
doctors, thirty clinics paying into one account, an identity recycled
across insurers. Fraud is relational, so the detection has to be
relational. That's the whole thesis, and it's why this is a graph database
and not a dashboard."

**What it actually does (45 s).** "A synthetic economy generator simulates
ten thousand patient journeys across five real medical-tourism corridors —
real countries, entirely fictional people. Then four detection rules run
over the graph: ghost clinics that bill without existing, one licence
number laundered across several identities, brokers taking kickbacks from
the clinics they steer to, and one passport being treated in two countries
on the same day. Each finding becomes a scored alert with the exact
evidence subgraph attached. Eighty-one alerts on the current dataset."

**Why you should believe any of it (45 s).** "Three things. The thresholds
were calibrated only on the *honest* half of the economy — zero medium or
high alerts there, so I'm not tuning against my own fraud. The fraud isn't
labelled in the data; it emerges from incentive parameters on actors, so
ground truth is derived, not planted. And the held-out test was
hash-committed before any detection code existed, then run once under a
pre-registration that said I wouldn't change anything based on the
results. Five of eight, three misses, two root causes — all published."

**Timing target: 2:45–3:15.**

---

## The 10-minute pitch — runnable script

Format: **[cumulative time] BEAT — what you click — what you say.** The
say-lines are prompts, not a word-for-word recitation; the *bolded*
sentences are load-bearing and should come out close to verbatim.

### [0:00 → 1:00] HOOK — *no clicks, console already open on the queue*

Stand still. Do not touch the laptop.

> "One patient flies from London to Chennai for cardiac surgery. That
> single journey touches five record-keepers: their home insurer, the
> treating clinic, the broker who arranged the trip, and two countries'
> health systems. **No one of them ever sees the whole chain.**
>
> Fraud lives in that gap. Ghost clinics billing for surgery that never
> happened. One doctor's licence number behind four identities. A broker
> recycling the same patient across insurers. **Every one of those records
> looks completely fine on its own — the fraud only exists in the
> relationships between them.**
>
> I built the system that sees the relationships."

**Exit at 1:00.** If you're over, cut the ghost-clinic list to two items.

### [1:00 → 2:00] THE INSIGHT — *still no clicks*

> "Fraud detection today is per-claim. One insurer scores one claim against
> its own historical data. That catches a claim that looks wrong — and
> organised fraud is engineered so that no claim ever looks wrong.
>
> **Detection that can't see the network can't see the fraud.** That's not
> a tooling gap, it's a category error. So: a graph database, where the
> shared endpoints *are* the query. Four typologies shipping — ghost
> clinics, credential laundering, kickback rings, impossible travel. Two
> more fully specified with their false-positive modes, as the next build.
> I'd rather ship four I can defend than six I can't."

### [2:00 → 2:45] WHAT I BUILT — *gesture at the header, don't click*

> "Synthetic economy generator, Neo4j graph, detection layer, investigator
> console. Fifty-two thousand nodes, two hundred thousand relationships,
> eighty-one alerts — and those alerts are *precomputed and committed*, so
> a fresh clone boots in twenty-one seconds and never runs detection.
> **Everything you're about to see is running offline on this laptop.
> There is no network in this demo and no API call anywhere in it.**"

### [2:45 → 6:15] LIVE DEMO — *the click path*

**[2:45] Click nothing yet.** Point at the queue header.
> "Eighty-one alerts, sorted by risk. The colour band down the left is
> severity — an investigator starts at the top and works down."

**[3:00] Click the `impossible_travel` chip.** Wait for the filter.
> "Let me start with the one that needs no explanation."

**[3:10] Click ALT_000068.** *Let the graph render. Say nothing for two
seconds — this is the money shot.*
> "One passport. Two patient identities. Two countries. **Same day.** One
> person cannot be on two operating tables in two countries on the same
> date — that isn't improbable, it's impossible. The two circled nodes are
> the identities; the two grey ones are the claims that collide."

**[3:40] Point at the evidence panel — do not scroll it.**
> "The panel tells you which rule fired and the exact numbers it fired on.
> A rule that can't explain itself is useless to an investigator who has to
> justify freezing a payout."

**[4:00] Point at the narration panel.**
> "Plain-English brief. It's tagged *pre-generated* because it was written
> at build time and committed to the repository — **there is no API call at
> demo time, by design. The venue has no network and I assumed that from
> day one.**"

**[4:20] Click `reviewed`, type nothing, or type one word.**
> "Triage state persists — that's the investigator workflow, not a demo
> toy."

**[4:35] Click ← Queue, clear the filter, click ALT_000062 (ghost clinic).**
*Let it render.*
> "Now the one that shows what the graph is actually for. Fifty-six claims.
> **Zero beds.** One doctor covering all fifty-six. One broker feeding
> ninety-five percent of them. One account receiving every payout. And
> every single patient visited exactly once and never appears anywhere else
> in the economy.
>
> **Every one of those claims looks fine on its own. The fraud is only
> visible in what they share.**"

**[5:30] Point at the evidence panel's first line.**
> "Five of six indicators fired. Not one — five. Each has an innocent twin;
> day clinics do have zero beds, small clinics do bank in one place. The
> *combination* is what doesn't occur among the legitimate clinics in this
> economy, and that's why the score is eighty-five and not thirty."

**[6:00] Back to queue.**
> "Four typologies, one console, and adding a fifth is a YAML file and a
> query — no API change, no frontend change."

**Exit at 6:15.** If you're at 6:30+, drop the last line and move.

### [6:15 → 7:45] HOW I KNOW IT WORKS — *no clicks; this is the section that wins or loses technical judges*

> "You should be suspicious of anyone who generates their own fraud and
> then finds it. So here is exactly what I did about that.
>
> **One:** the honest economy came first, and the thresholds are calibrated
> only against it — zero medium-or-high alerts on honest actors, for every
> rule. I never tuned against fraud labels.
>
> **Two:** the fraud isn't labelled. Actors get incentive parameters and
> the patterns emerge from their interactions, so ground truth is derived
> afterwards, not planted.
>
> **Three, and this is the one I'd want to be judged on:** before I wrote a
> single detection query, I authored five held-out fraud scenarios, stored
> them outside the repository, and committed their SHA-256 hashes. That
> commit is in the history, and it predates every line in the detection
> directory. Then, before opening them, I committed a pre-registration: no
> rule, threshold, or parameter would change based on the results, and
> misses would be published as they landed. Then I ran it once.
>
> **Eight detection legs expected across five scenarios. Five detected.
> Three missed. Two root causes — and I did not fix either one, because
> fixing them after the fact would have destroyed the only thing that makes
> the number meaningful.**"

*(Then the two root causes — see [the held-out numbers](#the-held-out-numbers--exact-say-them-this-way) below. Deliver both, flatly, ~35 s.)*

> "What this proves is *ordering*, not independence. The same person wrote
> the scenarios and the rules; no hash can separate what one brain knew.
> It's a discipline claim, and I'd rather give you a discipline claim I can
> prove than an independence claim I can't."

### [7:45 → 8:45] ARCHITECTURE & HONEST LIMITS

> "Neo4j because the signals are traversals and community structure —
> that's what SQL is worst at. Batch detection writing alert nodes, because
> a live demo should never wait on an algorithm and because a new typology
> then needs zero API changes. And one measured decision I'd point at:
> the kickback rule was designed to use betweenness centrality. I measured
> it — **a hundred and thirty-two seconds on fifty-one thousand nodes, and
> it ranked the true steering brokers worse than a one-line concentration
> query. So I cut it.** It's in the decision log with the benchmark.
>
> What production needs that this doesn't have: a data-sharing consortium —
> which is a legal problem, not a technical one — entity resolution on
> messy real identifiers, and Neo4j Enterprise for access control between
> competing insurers. **I know where the prototype ends.**"

### [8:45 → 10:00] WHO BUYS IT + CLOSE

> "Insurers and reinsurers lose the money. Third-party administrators
> already process claims for many insurers at once, which makes them the
> wedge — they can see cross-insurer patterns today and have no tooling for
> it. Accreditation bodies need evidence to revoke clinics that exist only
> on paper.
>
> This was planned as a five-person build. It became one person and
> thirteen days. Everything you've seen — the generator, the graph, the
> detection, the API, the console, the evaluation protocol — is in the
> repository with a decision log explaining every choice and its
> alternatives. **I wrote every line, so ask me about any of it.**"

**Stop talking. Do not fill silence.**

---

## Self-scoring rubric (no audience needed)

Record yourself on your phone. Play it back at 1× (not 1.5× — you need to
hear the pauses). Score each section pass/fail *before* looking at the
notes, then read the failure modes.

| section | "good" sounds like | 3 most common failure modes | pass = |
|---|---|---|---|
| **Hook** (0:00–1:00) | Slow. Conversational. You are telling someone about a problem, not reciting. The two bolded sentences land in silence around them. | (1) Rushing — you're 15 s under and it sounds nervous. (2) Hands on the laptop. (3) Listing four typologies here instead of one image. | You hit 55–65 s, and the "every record looks fine" line has a pause on both sides of it. |
| **Insight** (1:00–2:00) | Confident, almost blunt. "Category error" delivered as fact, not opinion. | (1) Apologising for only four typologies. (2) Explaining Neo4j's features instead of the *reason*. (3) Drifting into architecture early. | You say why-graph in one sentence and don't mention any technology name except Neo4j once. |
| **What I built** (2:00–2:45) | Brisk. Numbers spoken cleanly, no hedging. | (1) Guessing a number. (2) Over-explaining the generator. (3) Forgetting the offline line. | All four numbers correct from memory, offline line delivered. |
| **Demo** (2:45–6:15) | Your hands are ahead of your mouth: you click, *then* speak into the loaded view. Two full seconds of silence after the travel graph renders. | (1) Narrating your own clicking ("now I'll click here"). (2) Talking over a loading graph. (3) Scrolling the evidence panel while talking. | You never say "now I'm going to…", and both money lines land while the relevant view is already on screen. |
| **How I know it works** (6:15–7:45) | Unhurried and specific. The miss count is stated as plainly as the catch count. | (1) Softening the misses ("only three"). (2) Overclaiming independence. (3) Speeding up because it's uncomfortable. | You say "three missed" without adding a qualifier, and you say "ordering, not independence" out loud. |
| **Architecture & limits** (7:45–8:45) | Two concrete decisions with numbers, then limits without flinching. | (1) Listing every ADR. (2) Defensive tone on limits. (3) Skipping the betweenness story — it's your best engineering moment. | Betweenness number said aloud; at least two production gaps named unprompted. |
| **Close** (8:45–10:00) | Steady. The last line is an invitation, not a plea. Then silence. | (1) Trailing off. (2) Apologising for the team collapse. (3) Continuing to talk after "ask me about any of it". | You stop cleanly and stay stopped for three seconds. |

**Whole-run pass:** finished between 9:30 and 10:00, zero invented numbers,
no filler ("um, basically, kind of"), and you did not touch the laptop
during the hook or the closing.

**If you fail the same section twice, that section's script is wrong for
your voice — rewrite that section's wording, not your delivery.**

---

## The 15 questions, ordered by likelihood

Answers are skeletons: the beats that must come out, not a recitation.
Deeper drills and area-by-area material: [DEFENCE_AREAS.md](DEFENCE_AREAS.md).

**1. "You generated the fraud yourself — didn't you just find what you
planted?"** *(near-certain; the whole project is judged on this answer)*
Four beats, in order: honest economy first and thresholds calibrated only
on it (zero medium+ on honest actors); fraud is *parameterised*, not
labelled, so ground truth is derived; held-out scenarios hash-committed
before any detection query existed; pre-registration committed before
opening them, results published including three misses. Then the limit,
unprompted: ordering, not independence.

**2. "Why is this not just a database with some queries?"** *(very likely,
and it's a trap for a weak answer)*
"It is queries — over a data model where the join *is* the signal. Try it
in SQL: 'find identities sharing a passport, treated in different
countries, within a window' is a self-join over claims plus a date
predicate; 'find dense clusters of brokers, clinics and accounts nobody
labelled' is community detection, which has no SQL formulation at all. I
use Louvain for exactly that. The honest version: two of my four rules
*could* be SQL with effort; the value is that all four live over one
traversal model, and adding a fifth is a YAML file, not a schema
migration."

**3. "Why did you miss three of eight?"** *(certain, since you volunteer
the number)*
See [the held-out numbers](#the-held-out-numbers--exact-say-them-this-way);
give both root causes, then: "Both fixes are specified. Neither is applied,
because the pre-registration said no changes based on results — and a
number I can't be accused of tuning is worth more than a number I fixed."

**4. "What happens at ten million nodes?"** *(very likely from a senior
engineer)*
"Three separate answers. The targeted queries hold — they're one-to-two
hops off constraint-backed indexes, so they scale with the neighbourhood,
not the graph. Louvain holds within a batch window. Exact betweenness does
*not* — it's O(n·m), I measured 132 seconds at fifty-one thousand nodes,
and at ten million that's hours; GDS's Brandes sampling reproduced 94% of
the exact top-50 at 5% of the cost, which is the documented fallback. And
honestly, Neo4j Community's single-database, no-RBAC limits bite before
any of the algorithms do — that's an Enterprise conversation."

**5. "What would you do with six more months?"** *(likely from recruiters
and investors both)*
"In order. One: real data through a TPA partnership — everything downstream
is guesswork until the distributions are real, and I'd expect my
thresholds to be wrong. Two: entity resolution, because real identifiers
are messy and my synthetic ones are clean — that's the single biggest gap
between this and production. Three: the two specified typologies plus the
composed-guard fix the held-out test found. Four: an unsupervised
embedding layer to catch what no rule anticipated — which only becomes
honest once there's real data. Notice ML is fourth, not first."

**6. "Why not machine learning?"**
"No labelled real-world data exists for this. Training on my own synthetic
labels would launder my assumptions into something that looks like
evidence — the circularity problem, with a neural network on top. Also,
an investigator has to justify freezing a payout; 'the model said 0.87'
doesn't survive that, 'five structural indicators fired, here they are'
does. The unsupervised parts — community detection, centrality — I do use,
because they find structure without needing labels."

**7. "Walk me through one typology end to end."** *(default to ghost
clinic; be ready for any)*
Behaviour → signature → features → score → FP modes. Ghost clinic: paper
clinic plus cooperating broker bills for procedures never performed;
signature is volume against footprint; features are claim count vs beds
and registration age, inflow concentration on one broker, payout
concentration on one account, doctors per claim, single-visit patient
share; weighted 0–100; documented FP modes are the honest new day clinic,
the exclusive referral partner, the single corporate account — which is why
one feature alone can't reach medium.

**8. "What are your false positives?"**
"Every rule has documented FP modes written *before* implementation. On the
honest economy, zero medium-or-high alerts across all four rules — the
low-severity tail is deliberate: those are shared licence numbers and
post-revocation billing that occur honestly, surfaced at low so an
investigator can clear them fast. Credential laundering has 56 low
false positives and I'd rather show you that number than hide it behind a
threshold."

**9. "How much of this did AI write?"**
"AI-assisted throughout, disclosed in the README rather than per-commit.
The standard I held myself to is in the project's own rules: nothing ships
that I can't explain aloud, unaided. That's what the last ten minutes
were, and it's what the next question will be too — so test it."

**10. "Where would real data come from? Who would share it?"**
"The technology is the easy half. TPAs already aggregate multi-insurer
flows — that's the wedge, one customer with the data already joined.
Second path is an accreditation consortium. Privacy law means hashed
identifiers, which my shared-endpoint signals survive better than
content-based ones do: I never need to know the passport number, only that
two records share one."

**11. "Why these four typologies and not the other two?"**
"Capacity, honestly. The cut order was written down before it was needed:
template cloning went first because its algorithmic risk was highest,
circular payment second because it was the least demo-critical. Both are
fully specified with their false-positive modes — that's a roadmap with
receipts, not a gap. Four I can defend beats six I can't."

**12. "How would you add a fifth typology right now?"** *(also the Day-2
answer)*
"A YAML registry entry plus a Cypher query or a Python module. The runner
writes alert nodes and implicates edges; the API and console need zero
changes because alerts are self-describing. I have it rehearsed as a
ninety-minute drill including a new node type end to end."

**13. "Why did the team become one person, and what did that change?"**
Flat, no drama: "It became one person early in the build. What changed is
in the decision log: I cut two typologies the same day rather than ship six
shallow ones, rewrote the schedule around one person's real hours, and
replaced the person-based part of the evaluation protocol — a red-team
member who'd never read the spec — with a time-based one, because ordering
is provable in git and person-independence no longer was."

**14. "Is any of this real patient data?"**
"None. Real countries and real procedure *categories*, because corridor
economics matter for realism. Every person, clinic, broker, insurer,
identifier and claim is generated fiction from a seeded simulation — same
seed, byte-identical output, which is also why the demo is reproducible."

**15. "What's the weakest part of this project?"**
*(Answer it honestly — the attempt to dodge is what loses the room.)*
"The generator is the foundation everything stands on, and I have no way
to validate that my synthetic distributions resemble real claim data,
because I've never seen real claim data. Everything downstream inherits
that. Second weakest: kickback recall — six of thirteen steering brokers,
because eight of them sit at or below the median referral volume where no
structural signal separates them from honest small brokers. That one I
measured and reported rather than tuned."

---

## The held-out numbers — exact, say them this way

**Do not paraphrase these figures. A judge will do the subtraction while
you talk.**

> "Five scenarios. Eight detection legs expected across them — S5 was a
> composite that should have tripped all four rules. **Five legs detected.
> Three legs missed.** Every one of the five scenarios raised at least one
> alert, but three of the eight expected legs did not fire.
>
> The three misses come from **two root causes**, and both are limitations
> in my rules, not accidents:
>
> **Two of the three misses are the same defect.** My credential rule has
> two false-positive guards: shared licence numbers only count within one
> issuing body, and post-revocation billing is suppressed when the doctor
> holds another valid credential. Each guard is individually justified by
> the honest data. **Composed, they leave a gap** — a licence shared
> *across* jurisdictions, held by a doctor who kept one valid credential,
> passes both guards. It missed that in two different scenarios. The fix is
> scoring the signals together instead of gating them sequentially; it's
> specified and unapplied.
>
> **The third miss is a deliberate conservatism.** My travel rule only
> flags what is physically impossible — same-day treatment in two
> countries. One scenario used gaps of two to twenty-six days: suspicious,
> but possible, and the rule refuses to call a possible thing impossible.
> That's why it produced zero medium-or-high false positives across ten
> thousand honest patients. Catching feasible-but-suspicious reuse needs a
> frequency signal, which is the typology's second axis and isn't built."

**Then the limit, always:**
> "And what the protocol proves is ordering, not independence. I wrote both
> sides. The hashes prove the test existed before the code; the
> pre-registration proves I didn't tune after seeing results. No hash can
> prove one brain didn't unconsciously write scenarios its own rules would
> catch."

**Consistency check (same numbers, three places):** this section,
[README.md](../README.md) validation section, and
[HELDOUT_COMMITMENT.md](HELDOUT_COMMITMENT.md) evaluation record. If you
ever change one, change all three in the same commit.

---

## Fallback path (rehearse this, don't improvise it)

If anything hangs: **stop clicking, keep talking, open the screenshot
deck** (`screenshot-deck/`, seven beats, already open on a second desktop).
The deck is a rehearsed mode, not an apology — "I'll show you the rest from
the deck; the whole run is also recorded" costs you three seconds and no
credibility. Recovery rules and drills: [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md).

## Rehearsal log

| date | run | time | pass? | what broke |
|---|---|---|---|---|
| | | | | |
