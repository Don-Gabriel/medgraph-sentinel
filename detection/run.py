"""Batch detection runner — registry-driven (docs/INTERFACES.md section 5).

Currently a conforming no-op: no rules are registered yet (M3 builds them).
Exits 0 with an empty summary so the compose `seed` service (loader &&
detection) succeeds as soon as the loader exists.
"""
import json
import sys


def main() -> int:
    summary = {"rules_run": [], "alerts_written": {}, "duration_s": 0.0}
    json.dump(summary, sys.stdout)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
