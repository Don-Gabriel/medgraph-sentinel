# Cold Start — The Hand-Run Offline Drill

The exact sequence for the offline acceptance test (ADR-019, two runs:
discovery **Aug 4–5**, confirmation **Aug 10**) and for disaster recovery
at the venue. Written for a tired person on any Docker-capable machine.
Every command is copy-pasteable into PowerShell. **Nothing in this
sequence needs the internet after step 2.**

The bundle lives at `C:\WorkSpace\Private\medgraph-demo-usb\`, staged
2026-07-31 (measured): `medgraph-images.tar` **475 MB**,
`medgraph.bundle` **9.7 MB**, the 7 deck PNGs and `demo-recording.webm`
loose (**8.4 MB**), `RESTORE.txt` — **493 MB total.** Any USB stick of
1 GB+ works.

**Freshness check, before Phase 1:** run
`git bundle list-heads C:\WorkSpace\Private\medgraph-demo-usb\medgraph.bundle`
and confirm its `refs/heads/main` equals `git rev-parse main` in the repo.
If main has moved (docs-only merges have landed since the staging), rebuild
with the commands in DEMO_RUNBOOK's **Export** block (`docker compose
build` → `docker save` → `git bundle create --all`) before copying to
the stick.

**The screenshot deck and the demo recording are committed to the repo**, so
they are already inside `medgraph.bundle` — nothing extra to remember at
export time. After cloning (step 8) they are at
`screenshot-deck/` (7 PNGs, 1920×1080) and `demo-recording.webm`. Copy both
loose onto the stick as well: if Docker itself is dead, the stick must hand
you the fallback deck without a git clone standing between you and it.

## Phase 1 — copy to USB (one-time, online is fine)

1. Plug in the USB stick, note its drive letter (assume `E:` below).
2. Copy the three files:

```
copy C:\WorkSpace\Private\medgraph-demo-usb\* E:\
```

3. Eject cleanly (taskbar → Safely Remove). Done — the stick is the demo.

## Phase 2 — go offline (the part only a human can do)

4. **Disable the network.** Either: click the network icon in the system
   tray → **Airplane mode ON**; or Device Manager → Network adapters →
   right-click each adapter → **Disable device**. Airplane mode is easier
   and enough.
5. Confirm: open a browser, try any website — it must fail. If it loads,
   you are not offline; stop and fix that first. **Stay offline through
   step 12.**

## Phase 3 — cold state (makes the test honest)

6. Prove no warm images exist (this is what makes a pass meaningful):

```
docker image ls
```

   If any `medgraph-*` images are listed, remove them (the running demo
   must be stopped first: `docker compose down` in the repo):

```
docker image rm medgraph-neo4j:demo medgraph-api:demo medgraph-frontend:demo
```

## Phase 4 — restore from the stick (still offline)

7. Load the images (~1 minute):

```
docker load -i E:\medgraph-images.tar
```

8. Clone the repo from the bundle into a scratch folder:

```
git clone E:\medgraph.bundle C:\coldtest\medgraph-sentinel
```

```
cd C:\coldtest\medgraph-sentinel
```

9. Create the env file (any password, 8+ characters — this is a fresh
   database):

```
copy .env.example .env
```

```
notepad .env
```

   Set `NEO4J_PASSWORD=coldtest-2026` (and on a 16 GB+ machine,
   `NEO4J_HEAP_SIZE=4G`, `NEO4J_PAGECACHE_SIZE=2G`). Save, close.

10. Boot — **no pull, no build, no network**. Time it (target ≤ 3 min to
    healthy):

```
docker compose up -d
```

```
docker compose ps
```

    Re-run `ps` until neo4j and api say `healthy` and seed says
    `Exited (0)`.

## Phase 5 — verify (the pass criteria)

11. Open `http://localhost:8000/api/v1/health` — must show
    `"status":"ok"`, `"alert_count":81`, `"match":true`. Anything else is
    a FAIL — write down exactly what it said.
12. Open `http://localhost:5173` — the queue must show **81 alerts**.
    Open three alerts across different typologies; each narration panel
    must be tagged **"pre-generated AI narration"** (not "deterministic
    fallback" — fallback here means the cache didn't ship, which is a
    FAIL of step 7/8, not a cosmetic issue).
13. Record: total time from step 7 to step 12, and any step that
    deviated. That record goes into DEMO_RUNBOOK's timing table.

## Phase 6 — back to normal

14. Re-enable the network (Airplane mode OFF / re-enable adapters).
15. Clean up the scratch clone when satisfied:

```
docker compose down -v
```

```
cd C:\ && rmdir /s /q C:\coldtest
```

    (Your real working copy at `C:\WorkSpace\Private\medgraph-sentinel`
    is untouched by any of this; restart its stack with
    `docker compose up -d` from that folder.)

## If something fails

- **Step 7 fails** → the tarball is damaged: rebuild it online
  (`docker compose build` then the `docker save` line in DEMO_RUNBOOK)
  and re-copy.
- **Step 10 tries to pull/build** → the images didn't load or tags
  drifted; re-run step 7 and check `docker image ls` shows all three
  `*:demo` tags.
- **Step 11 shows `match:false`** → the clone and the images disagree
  about alerts (partial copy?); re-clone from the bundle.
- **Anything else** → screenshot the error, re-enable network, fix at
  leisure. That is exactly why this drill runs on Aug 4–5 and not for
  the first time on Aug 10.
