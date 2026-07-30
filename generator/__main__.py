"""Generator CLI. Contract: docs/INTERFACES.md §2-3.

    python -m generator --seed 42 --out data/ [--scenario file.yaml ...]

Pass order matters for byte-determinism (ADR-006): honest economy →
emergent fraud → parallel-recycling additions → planted cells → scenario
overlays (sorted by scenario name). Every later pass draws from the same
single numpy Generator strictly AFTER the earlier ones, so switching a
later layer off never changes an earlier layer's bytes — and a run with no
scenarios is bit-for-bit unaffected by overlay support existing.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
from faker import Faker

from . import economy, fraud, plant, scenario, writer
from .config import load_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m generator")
    parser.add_argument("--seed", type=int,
                        default=int(os.environ.get("GENERATOR_SEED", "42")))
    parser.add_argument("--out", type=Path, default=Path("data"))
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--scenario", type=Path, action="append", default=[],
                        help="scenario overlay YAML (INTERFACES §3); repeatable")
    args = parser.parse_args(argv)

    # parse + validate every scenario before any generation work
    scenarios = [scenario.load_scenario(p) for p in args.scenario]
    names = [s.scenario for s in scenarios]
    if len(names) != len(set(names)):
        print(f"generator: duplicate scenario names in {sorted(names)}",
              file=sys.stderr)
        return 2
    # applied in sorted-name order so the same scenario SET is byte-identical
    # regardless of flag order
    scenarios.sort(key=lambda s: s.scenario)

    cfg, config_sha = load_config(args.config)
    rng = np.random.default_rng(args.seed)
    Faker.seed(args.seed)
    fake = Faker()

    world = economy.World()
    economy.build_static(cfg, rng, fake, world)
    params = fraud.assign(cfg, rng, world)
    economy.build_journeys(cfg, rng, fake, world, params)
    fraud.side_payments(cfg, rng, world, params)
    fraud.parallel_recycling(cfg, rng, fake, world, params)
    planted_rows = plant.plant(cfg, rng, fake, world)
    scenario_truth = {
        s.scenario: scenario.apply_scenario(cfg, rng, fake, world, params, s)
        for s in scenarios
    }
    manifest = writer.write_all(world, args.out, args.seed, config_sha,
                                params.ground_truth, planted_rows, scenario_truth)

    total_nodes = sum(
        v for k, v in manifest["counts"].items() if not k.startswith("rel_")
    )
    total_rels = sum(v for k, v in manifest["counts"].items() if k.startswith("rel_"))
    json.dump({"seed": args.seed, "nodes": total_nodes, "relationships": total_rels,
               "scenarios": manifest["scenarios_applied"], "out": str(args.out)},
              sys.stdout)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
