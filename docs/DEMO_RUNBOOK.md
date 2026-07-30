# Demo Runbook

Assumption baked into everything here (owner decision Q3): **the venue has no
usable network and an untrustworthy projector.** The demo must be complete
and impressive from local Docker on the demo laptop, cold.

Executed in full on the actual demo laptop (OQ #9) at the Aug 10 dress
rehearsal — including the cold-start acceptance test below. Every drill gets
run at least once before Aug 12.

## One-way demo build chain (ADR-018)

The narration cache is keyed by alert ID; alert IDs are assigned per
detection run. **Any regeneration or detection re-run after the cache is
built silently orphans every cached narration** — the API would degrade to
template text mid-demo without an error. So the demo artifacts are built
strictly one way (scheduled Aug 7, MILESTONES):

```
freeze dataset → run loader → run detection → build narration cache
             → commit (dataset + alerts + cache together) → NO regeneration
```

Rules:

- After the chain has run, `data/` and detection are **frozen**. A
  post-freeze fix that touches either re-runs the **entire chain from the
  top** and re-commits it as one unit — never partially.
- The Aug 9 held-out evaluation and any Day-2 scale test use separate data
  directories; they never touch the committed demo artifacts.
- The guard rail is automatic (INTERFACES §6): on startup the API compares
  cached-narration count against alert count and, on mismatch, logs
  `CRITICAL NARRATION CACHE MISMATCH` and reports `narration_cache.match:
  false` at `/health` with status `degraded`. **Checking `/health` after
  every boot is part of this runbook** — a mismatch on Aug 10–12 means: stop,
  re-run the chain, re-commit.

## Image distribution — build once, carry on USB (ADR-019)

`docker compose up` pulling Neo4j or building the API/frontend images at the
venue is our single largest offline risk — bigger than the Claude API, which
the committed cache already covers. So images are built at home and carried
as files. (Image names are pinned in `docker-compose.yml` — the three
`*:demo` tags below are the real ones, so these commands are
copy-pasteable as-is.)

**Export (on a machine that has built everything, by Aug 9):**

```bash
# builds medgraph-api, medgraph-frontend AND medgraph-neo4j (GDS is baked
# into our own neo4j image at build time — ADR-026; a plain pull of
# neo4j:5.26-community would NOT contain GDS and would try to download it
# at the venue)
docker compose build
docker save -o medgraph-images.tar \
  medgraph-neo4j:demo medgraph-api:demo medgraph-frontend:demo
git bundle create medgraph.bundle --all   # full repo incl. dataset + caches
```

**Restore (any Docker machine, no network):**

```bash
docker load -i medgraph-images.tar
git clone medgraph.bundle medgraph-sentinel
cd medgraph-sentinel && cp .env.example .env   # set NEO4J_PASSWORD + profile
docker compose up -d
```

**USB stick manifest — two sticks, identical, prepared Aug 11, checked off
per stick:**

- [ ] `medgraph-images.tar` (all three images, one tarball)
- [ ] `medgraph.bundle` (full git bundle: repo + committed dataset
      `data/csv/` + manifest + ground truth + committed narration cache
      `api/narration_cache/`)
- [ ] A plain full clone of the repo (belt for the bundle's braces —
      usable without any git knowledge under stress)
- [ ] `screenshot-deck/` (the fallback deck, exported Aug 10)
- [ ] `demo-recording.mp4` (screen recording, Aug 10)
- [ ] `RESTORE.txt` — the restore commands above, verbatim

The dataset and narration cache ride *inside* the bundle/clone because they
are committed (ADR-005/010); they are listed separately here so their
presence is verified explicitly, not assumed.

## Cold-start acceptance test (ADR-019 — the test that counts)

**Validity rule: this test passes only on the DEMO LAPTOP, at the Aug 10
dress rehearsal, from a genuinely cold start.** A pass on a machine that has
been online with images already in its local Docker cache proves nothing —
warm caches are exactly the failure we're hunting. If step 3 finds existing
project images, remove them first or the run is void.

1. Disable the demo laptop's network adapter (airplane mode / adapter
   disabled in OS settings). It stays disabled through step 10.
2. Plug in USB stick #1.
3. `docker image ls` — confirm **no** `neo4j`, `medgraph-api`, or
   `medgraph-frontend` images present; `docker image rm` any found (this is
   what makes the start cold).
4. `docker load -i medgraph-images.tar` — completes without network.
5. `git clone medgraph.bundle medgraph-sentinel-coldtest` — completes
   without network.
6. `cp .env.example .env`, set `NEO4J_PASSWORD` and the machine's memory
   profile.
7. `docker compose up -d` — no pull, no build, no error. Time it.
8. `/api/v1/health` returns `status: "ok"`, `neo4j: true`, and
   `narration_cache.match: true`.
9. Console at `localhost:5173` shows the alert queue with real alerts.
10. Open three alerts across different typologies: each narration panel
    shows `source: "claude-cached"` — **cached, not `fallback`/template**.

Pass = all ten steps, network disabled throughout, total time from step 4 to
step 9 recorded in the timing table below. Repeat once with USB stick #2
(steps 2–4 only, into a scratch directory) to prove both sticks are good.

## Pre-venue checklist (complete by Aug 11 evening)

- [ ] Demo laptop identified and confirmed (OQ #9); memory profile set in
      `.env`; **cold-start acceptance test passed on this machine Aug 10**.
- [ ] Docker Desktop healthy on demo + backup laptop; both hold the loaded
      images.
- [ ] Both USB sticks match the manifest above (item-by-item check).
- [ ] Narration cache committed; `/health` shows `narration_cache.match:
      true`; spot-check 3 alerts show `source: claude-cached`.
- [ ] Screenshot deck exported (every demo beat, full-res) — on both laptops
      and both USBs.
- [ ] Screen-recorded full demo run (Aug 10) on both laptops.
- [ ] HDMI *and* USB-C→HDMI adapters; chargers; a mouse.
- [ ] Browser profile prepared: console pinned tab, 125% zoom checked on a
      TV/projector, notifications off, night-light off.
- [ ] OS updates paused; battery full; performance power plan; auto-sleep
      off.
- [ ] `.env` verified — **no API key needed** (offline posture); live
      narration path confirmed disabled regardless.

## Boot sequence (venue, before pitch slot)

1. Power + charger. Wifi OFF deliberately — we demo air-gapped and say so.
2. `docker compose up -d` from the standing clone (NOT a fresh clone at the
   venue). Wait for healthchecks (`docker compose ps` all healthy).
3. **Check `/api/v1/health`: `narration_cache.match` must be `true`** — a
   mismatch here means someone broke the ADR-018 chain; fall back to the
   backup laptop's clone rather than debugging on stage.
4. Open the console, click through the *entire* demo path once (warms
   caches, confirms alerts + cached narrations). Leave it on the queue.
5. Do not touch it again until the pitch.

## Failure drills (each rehearsed with a named first responder)

**Wifi absent / captive portal nonsense** — no action; nothing needs
network. This is a pitch line, not a failure.

**Projector fails / no signal (Pavithra):** swap adapter (10 s), swap HDMI
port (10 s). If dead in 30 s: present from the laptop screen, jury gathered —
Pavithra narrates larger, Don angles the screen. Decided in advance so nobody
debates it live.

**Console hangs / white screen (Don Gabriel):** hard refresh (cached SPA —
usually enough). If dead in 15 s: Pavithra switches to the screenshot deck
mid-sentence (rehearsed handoff), Don restarts the frontend container in the
background; return to live only at a beat boundary (never mid-beat).

**API/Neo4j container down (Don Gabriel):** `docker compose restart api` /
`docker compose up -d` (~60–90 s under the screenshot deck's cover). If the
Neo4j data volume is corrupted: `docker compose down -v && docker compose up
-d` re-seeds deterministically in ~3 min — only viable before the slot, so
the boot-sequence click-through exists precisely to catch this early.

**Docker itself broken on demo laptop (whole team):** backup laptop (same
loaded images, same rehearsal) takes over; the USB tarball restores images
anywhere Docker runs. If both laptops fail: screenshot deck + screen
recording — the pitch survives with zero live software.

**Escalation rule:** any fix that hasn't worked in 30 seconds → screenshot
deck, no second attempts on stage. The deck is a rehearsed first-class mode,
not an apology.

## Timing reality (measured, not aspirational)

Record at dress rehearsal; update this table:

| step | target | measured Aug 10 |
|---|---|---|
| cold start: `docker load` → browsable console (acceptance test steps 4–9) | ≤ 6 min | |
| compose up → all healthy (images present) | ≤ 3 min | |
| fresh clone → browsable (post-load) | ≤ 3 min | |
| console full click path | ≤ 4 min | |
