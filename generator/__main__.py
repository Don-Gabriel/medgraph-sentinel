"""Generator CLI. Contract: docs/INTERFACES.md §2.

    python -m generator --seed 42 --out data/

NOTE: no --scenario flag yet — scenario-overlay handling (INTERFACES §3)
waits on the OQ #12 attestation before it is built, so that the red-team
member's tooling needs are designed with the isolation rule settled.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
from faker import Faker

from . import economy, fraud, writer
from .config import load_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m generator")
    parser.add_argument("--seed", type=int,
                        default=int(os.environ.get("GENERATOR_SEED", "42")))
    parser.add_argument("--out", type=Path, default=Path("data"))
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args(argv)

    cfg, config_sha = load_config(args.config)
    rng = np.random.default_rng(args.seed)
    Faker.seed(args.seed)
    fake = Faker()

    world = economy.World()
    economy.build_static(cfg, rng, fake, world)
    params = fraud.assign(cfg, rng, world)
    economy.build_journeys(cfg, rng, fake, world, params)
    fraud.side_payments(cfg, rng, world, params)
    manifest = writer.write_all(world, args.out, args.seed, config_sha, params.ground_truth)

    total_nodes = sum(
        v for k, v in manifest["counts"].items() if not k.startswith("rel_")
    )
    total_rels = sum(v for k, v in manifest["counts"].items() if k.startswith("rel_"))
    json.dump({"seed": args.seed, "nodes": total_nodes, "relationships": total_rels,
               "out": str(args.out)}, sys.stdout)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
