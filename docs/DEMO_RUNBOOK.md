# Demo Runbook

Assumption baked into everything here (owner decision Q3): **the venue has no
usable network and an untrustworthy projector.** The demo must be complete
and impressive from local Docker on the demo laptop, cold.

Executed in full on the actual demo laptop (OQ #9) at the Aug 10 dress
rehearsal. Every drill below gets run at least once before Aug 12.

## Pre-venue checklist (complete by Aug 11 evening)

- [ ] Demo laptop identified and confirmed (OQ #9); 16 GB profile in `.env`
      (or 8 GB profile if the machine demands it — both rehearsed).
- [ ] Docker Desktop healthy; `docker compose up` from a **fresh clone** on
      this exact machine timed and passing (target ≤ 3 min post-pull).
- [ ] All images pre-pulled on the demo laptop **and** one backup laptop.
- [ ] `docker save` tarball of all four images + a zip of the repo on **two
      USB sticks** (belt and braces; venue wifi is assumed absent).
- [ ] Narration cache committed and spot-checked (open 3 alerts, confirm
      `source: claude-cached`).
- [ ] Screenshot deck exported (every demo beat as a full-res image) — the
      projector-failure and total-failure fallback. Lives on both laptops
      and both USBs.
- [ ] Screen-recorded full demo run (Aug 10) on both laptops — the nuclear
      fallback.
- [ ] HDMI *and* USB-C→HDMI adapters packed; laptop chargers; a mouse.
- [ ] Browser profile prepared: console pinned tab, 125% zoom checked on a
      TV/projector, notifications off, night-light off.
- [ ] OS updates paused; battery full; power plan set to performance;
      auto-sleep off.
- [ ] `.env` on the demo laptop verified — **no real API key needed**
      (offline posture); if one is present, confirm the live-call path is
      disabled anyway.

## Boot sequence (venue, before pitch slot)

1. Power + charger. Wifi OFF deliberately — we demo air-gapped and say so.
2. `docker compose up -d` from the standing clone (NOT a fresh clone at the
   venue). Wait for healthchecks (`docker compose ps` all healthy).
3. Open console, click through the *entire* demo path once (warms caches,
   confirms alerts present). Leave it on the queue screen.
4. Do not touch it again until the pitch.

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
`docker compose up -d` (~60–90 s under the screenshot deck's cover). If
Neo4j data volume is corrupted: `docker compose down -v && docker compose up
-d` re-seeds deterministically in ~3 min — only viable before the slot, so
the boot-sequence click-through exists precisely to catch this early.

**Docker itself broken on demo laptop (whole team):** backup laptop (same
pre-pulled images, same rehearsal) takes over; USB tarball is the path if
the backup needs the images. If both laptops fail: screenshot deck + screen
recording — the pitch survives with zero live software.

**Escalation rule:** any fix that hasn't worked in 30 seconds → screenshot
deck, no second attempts on stage. The deck is a rehearsed first-class mode,
not an apology.

## Timing reality (measured, not aspirational)

Record at dress rehearsal; update this table:

| step | target | measured Aug 10 |
|---|---|---|
| compose up → all healthy (images present) | ≤ 3 min | |
| fresh clone → browsable (post-pull) | ≤ 3 min | |
| full image pull on venue-grade hotspot | n/a — never planned | |
| console full click path | ≤ 4 min | |
