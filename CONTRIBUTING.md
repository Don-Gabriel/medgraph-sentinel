# Contributing

Our git history is a work sample five people are being evaluated on
individually. These conventions exist so judges reading `git log` see five
engineers who work like a team.

## Identity

- Commit as **yourself**, with your real name and the email tied to your
  GitHub account. No shared accounts, no committing on someone else's
  behalf. We all work on **one shared laptop** (ADR-024) — see
  "Shared-machine identity" below for how to do this without
  cross-attributing commits.
- Pairing? The driver commits with a `Co-authored-by:` trailer for the
  navigator (GitHub renders both avatars).
- `Co-authored-by:` trailers name **human teammates only** — never a tool,
  bot, or third-party email address. This history is individually evaluated;
  AI assistance is disclosed once, in the README, not attributed per-commit.

## Shared-machine identity (one laptop — ADR-024)

Five people commit from one machine. Git identity is **repo-local state**,
so it must be switched at the start of your laptop slot and verified before
every commit:

1. **Start of your slot** — set the local identity (repo-local, so other
   repos on the machine are untouched):

   ```bash
   git config user.name  "Vijayalakshmi G"
   git config user.email "<the email tied to YOUR GitHub account>"
   ```

   Use your GitHub noreply address (`<id>+<user>@users.noreply.github.com`)
   if you keep your email private — attribution on GitHub follows the email.

2. **Before committing** — verify you are you:

   ```bash
   git config user.name && git config user.email
   ```

3. **After committing** — check the attribution stuck:
   `git log -1 --format='%an <%ae>'`. Wrong name? Fix it **before pushing**:
   `git commit --amend --reset-author` (after correcting the config).

4. **End of your slot** — switch the config back to the next person (in
   practice: whoever sits down next runs step 1; the sync order in
   MILESTONES makes this routine).

Never use `--author=` to commit "as" someone who isn't at the keyboard —
the committer field still records the machine identity, and the point is
that the named person actually did the work in their slot.

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

## Parallel work protocol — RETIRED (ADR-024)

The claim-before-work / collision-avoidance protocol assumed five people on
five machines. On one shared laptop there are no collisions to avoid; work
is sequenced by the laptop slots in MILESTONES instead. **INTERFACES.md
remains the contract** — its change protocol (announce first, `contract:`
PR prefix, same-commit updates on both sides of the seam) still applies in
full, because contracts are what make the modules explainable and Day-2
extensible, not just collision insurance. Push to GitHub at the end of
every session: the laptop is now a single point of failure.

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

## STATUS.md discipline

`docs/STATUS.md` is updated at the end of **every working session, by
whoever worked, in the same commit as their work** (multi-commit sessions:
the final commit). It is a snapshot, not a log — overwrite, don't append.
A stale STATUS.md is worse than none: the next person plans against it.

## The explain-aloud rule (from CLAUDE.md, binding here)

You merge it, you can explain it — and so should the reviewer. If either of
you can't say *why* a line exists, the PR isn't done. AI-assisted code is
fine; un-understood code is not. Judges will ask any of us about any module.
