"""Narration builder + deterministic fallback templates.

Contract: docs/INTERFACES.md section 8, ADR-010/018/032. Narrations are
pre-generated committed data (ADR-032): build.py imports all 81 texts into
the cache, refuses partial coverage, makes zero API calls. Nothing here may
read data/ground_truth/.

CACHE_DIR is the committed on-disk cache the offline demo serves from.
Modules reference it as `narration.CACHE_DIR` (not a from-import) so tests
can point it at a temp directory.
"""
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "narration_cache"
