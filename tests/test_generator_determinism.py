"""Same seed + config => byte-identical output (ADR-006), on a small world.

Runs the full pipeline twice into separate directories and compares SHA-256
of every emitted file. Small populations keep this test in seconds.
"""
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from generator.__main__ import main

SMALL_POPULATIONS = {"patients": 300, "doctors": 60, "clinics": 30, "brokers": 12,
                     "insurers": 6}


@pytest.fixture()
def small_config(tmp_path: Path) -> Path:
    base = yaml.safe_load((Path("generator") / "config.yaml").read_bytes())
    base["populations"] = SMALL_POPULATIONS
    p = tmp_path / "small.yaml"
    p.write_text(yaml.safe_dump(base), encoding="utf-8")
    return p


def _digest_tree(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_same_seed_is_byte_identical(tmp_path: Path, small_config: Path):
    out_a, out_b = tmp_path / "a", tmp_path / "b"
    assert main(["--seed", "42", "--out", str(out_a), "--config", str(small_config)]) == 0
    assert main(["--seed", "42", "--out", str(out_b), "--config", str(small_config)]) == 0
    assert _digest_tree(out_a) == _digest_tree(out_b)


def test_different_seed_differs(tmp_path: Path, small_config: Path):
    out_a, out_b = tmp_path / "a", tmp_path / "b"
    main(["--seed", "42", "--out", str(out_a), "--config", str(small_config)])
    main(["--seed", "43", "--out", str(out_b), "--config", str(small_config)])
    assert _digest_tree(out_a) != _digest_tree(out_b)


def test_every_device_edged_and_sharing_present(tmp_path: Path, small_config: Path):
    """ADR-022: ownership implies a USED_DEVICE edge; sharing must survive
    into the edge table (it is the primary signal for typology 5)."""
    import csv

    out = tmp_path / "a"
    main(["--seed", "42", "--out", str(out), "--config", str(small_config)])
    with open(out / "csv" / "devices.csv", encoding="utf-8") as fh:
        device_ids = {row["id"] for row in csv.DictReader(fh)}
    users: dict[str, set[str]] = {}
    with open(out / "csv" / "rel_used_device.csv", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            users.setdefault(row["target_id"], set()).add(row["source_id"])
    assert set(users) == device_ids  # no orphan devices, no phantom edges
    assert any(len(u) > 1 for u in users.values())  # sharing visible


def test_manifest_counts_match_files(tmp_path: Path, small_config: Path):
    out = tmp_path / "a"
    main(["--seed", "42", "--out", str(out), "--config", str(small_config)])
    manifest = json.loads((out / "manifest.json").read_text())
    for name, count in manifest["counts"].items():
        lines = (out / "csv" / f"{name}.csv").read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) - 1 == count, name  # minus header
