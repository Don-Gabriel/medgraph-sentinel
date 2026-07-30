# Contributing

**Solo project as of 2026-07-30 (ADR-027): J Don Gabriel is the only
contributor.** This file used to coordinate five people; what survives is
everything that makes the git history a readable work sample and the
contracts that make the modules explainable and Day-2 extensible. The
retired multi-contributor sections (shared-machine identity switching,
claim-before-work, red-team review isolation) are in git history if anyone
asks how the team would have worked.

## Identity

- Commit as yourself (`J Don Gabriel`, the email tied to the `Don-Gabriel`
  GitHub account). One committer, consistently — the history is individually
  evaluated.
- `Co-authored-by:` trailers are not used. They may **never** name a tool,
  bot, or third-party email address. AI assistance is disclosed once, in the
  README — not attributed per-commit.

## Branches

- `main` must always build and demo. Nothing lands except through a PR —
  solo, the PR is still worth it: it batches a reviewable diff, gives CI a
  hook point, and keeps merge commits as milestones in the history.
- Short-lived branches, deleted after merge, named `<type>/<scope>-<slug>`:
  `feat/detection-rule-registry`, `fix/api-subgraph-cap`. Target lifetime
  < 48 h; if a branch is older, split the work.
- Rebase on `main` before opening the PR.

## Commits — Conventional Commits

`<type>(<scope>): <imperative summary ≤ 72 chars>`

- **Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `perf`.
- **Scopes:** `generator`, `graph`, `detection`, `api`, `frontend`, `ops`
  (compose/CI), `docs`, `repo`. One scope per commit; if you need two, you
  need two commits.
- Body (when the summary isn't obvious): *why*, not *what* — the diff shows
  what. Reference ADRs (`per ADR-008`) and open questions (`resolves OQ #4`).
- Small commits that each build. No `wip`, no `misc fixes`, no drive-by
  reformatting mixed into logic changes.

Examples:

```
feat(detection): ghost clinic rule v1 with inflow/payout dominance features
fix(loader): validate rel counts against manifest before declaring success
docs(decisions): ADR-025 — LOAD CSV chosen over admin import (resolves OQ #1)
contract: add min_severity filter to GET /alerts (INTERFACES §6)
```

## Interface contracts (unchanged — this is not team overhead)

`docs/INTERFACES.md` remains the contract layer even with one author,
because the contracts are what make each module explainable in isolation
and what make Day 2 a bolt-on instead of surgery. Changing a contract:

- PR title prefixed `contract:`; the PR description states what changed and
  why (this replaces the retired "announce in the group" step).
- The same PR updates this file, the affected code on both sides of the
  seam, and DECISIONS.md if the change reverses an ADR.

## Held-out discipline (ADR-027 — replaces red-team isolation)

The held-out scenario files live **outside the repository**; only their
SHA-256 hashes are committed (docs/HELDOUT_COMMITMENT.md). Until the
one-shot evaluation (planned Aug 9): do not open, paste, summarize, or
commit them — in any working session, including AI-assisted ones. Sessions
that write detection code must not have the scenario text in context
(DATA_GENERATION §5 "Session discipline").

## STATUS.md discipline

`docs/STATUS.md` is updated at the end of **every working session, in the
same commit as the work** (multi-commit sessions: the final commit). It is
a snapshot, not a log — overwrite, don't append. A stale STATUS.md is worse
than none: the next session plans against it.

## The explain-aloud rule (from CLAUDE.md, binding here)

You merge it, you can explain it. If you can't say *why* a line exists, the
PR isn't done. AI-assisted code is fine; un-understood code is not. Judges
will ask about any module — and there is exactly one person to ask.
