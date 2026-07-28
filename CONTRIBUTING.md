# Contributing

Our git history is a work sample five people are being evaluated on
individually. These conventions exist so judges reading `git log` see five
engineers who work like a team.

## Identity

- Commit as **yourself**, from your own machine, with your real name and the
  email tied to your GitHub account. No shared accounts, no committing on
  someone else's behalf.
- Pairing? The driver commits with a `Co-authored-by:` trailer for the
  navigator (GitHub renders both avatars).
- `Co-authored-by:` trailers name **human teammates only** — never a tool,
  bot, or third-party email address. This history is individually evaluated;
  AI assistance is disclosed once, in the README, not attributed per-commit.

## Branches

- `main` is protected in spirit: it must always build and demo. Nothing
  lands except through a PR.
- Short-lived branches, deleted after merge, named
  `<type>/<scope>-<slug>`: `feat/generator-honest-economy`,
  `fix/api-subgraph-cap`, `docs/detection-fp-modes`. Target lifetime < 48 h;
  if a branch is older, split the work.
- Rebase on `main` before opening the PR; same-day rebase after any
  `contract:` merge (INTERFACES change protocol).

## Commits — Conventional Commits

`<type>(<scope>): <imperative summary ≤ 72 chars>`

- **Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `perf`.
- **Scopes:** `generator`, `graph`, `detection`, `api`, `frontend`, `ops`
  (compose/CI), `docs`, `repo`. One scope per commit; if you need two, you
  need two commits.
- Body (when the summary isn't obvious): *why*, not *what* — the diff shows
  what. Reference ADRs (`per ADR-008`) and open questions (`resolves OQ #3`).
- Small commits that each build. No `wip`, no `misc fixes`, no drive-by
  reformatting mixed into logic changes.

Examples:

```
feat(detection): ghost clinic rule v1 with inflow/payout dominance features
fix(loader): validate rel counts against manifest before declaring success
docs(decisions): ADR-016 — LOAD CSV chosen over admin import (resolves OQ #1)
contract: add min_severity filter to GET /alerts (INTERFACES §6)
```

## Pull requests

- Small and single-purpose; reviewable in ≤ 10 minutes.
- **One approval required, not the author.** Anyone may review anything —
  reviewing outside your comfort zone is how fluid roles stay fluid.
- The author merges after approval and deletes the branch.
- PRs that change an INTERFACES.md contract: title prefixed `contract:`,
  announced in the group *before* opening (see INTERFACES change protocol).
- CI (if adopted per OQ #7) must be green before merge.

## Parallel work protocol (fluid roles need this — ADR-014)

1. **Claim before you start.** Post in the team group: what you're picking
   up, which module(s), expected finish. First claim wins; no silent starts.
   The daily sync (MILESTONES) is where tomorrow's claims get sorted.
2. **One claim = one branch = one PR.** Finish or explicitly release the
   claim; don't sit on three half-done branches.
3. **Two people needing the same seam** (e.g. both sides of an API change):
   pair on it in one branch with co-authored commits, or split strictly
   along the contract with the contract PR merged first.
4. **Touching a contract?** INTERFACES.md change protocol — announce first.
   "I didn't know it changed" must never be a sentence anyone says.
5. **Same-evening collision insurance:** rebase early, push your branch
   daily (even unfinished — branches are cheap, lost evenings aren't), and
   keep the claim list current.

## Red-team isolation (enforced in review — ADR-016)

`docs/DETECTION_SPEC.md` and the rule implementations under `detection/` are
**off-limits to the designated red-team member** — currently **Pavithra R**,
pending the OQ #12 attestation; DECISIONS.md records any reassignment — until
`docs/HELDOUT_COMMITMENT.md` contains the scenario hashes **and** the
held-out evaluation has been run and its results committed. Practical rules:

- Never request review from the red-team member on a PR touching
  `detection/` or DETECTION_SPEC.md.
- Don't paste spec or rule content into channels she reads; link to file
  paths instead of quoting.
- An accidental exposure is reported at the next sync and recorded in
  DECISIONS.md — it downgrades the evaluation claim (DATA_GENERATION §5), it
  is not a reason to hide anything.

## The explain-aloud rule (from CLAUDE.md, binding here)

You merge it, you can explain it — and so should the reviewer. If either of
you can't say *why* a line exists, the PR isn't done. AI-assisted code is
fine; un-understood code is not. Judges will ask any of us about any module.
