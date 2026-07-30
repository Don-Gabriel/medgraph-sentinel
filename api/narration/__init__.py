"""Narration builder + deterministic fallback templates.

Contract: docs/INTERFACES.md section 8, ADR-010/018. Builder (one cached
Claude call per top alert, model from ANTHROPIC_MODEL) lands Aug 7 with the
one-way build chain. Nothing here may read data/ground_truth/.

CACHE_DIR is the committed on-disk cache the offline demo serves from.
Modules reference it as `narration.CACHE_DIR` (not a from-import) so tests
can point it at a temp directory.
"""
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "narration_cache"
