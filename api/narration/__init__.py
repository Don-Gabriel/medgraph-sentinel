"""Narration builder + deterministic fallback templates.

Contract: docs/INTERFACES.md section 8, ADR-010/018. Builder (one cached
Claude call per top alert, model from ANTHROPIC_MODEL) lands Aug 7 with the
one-way build chain. Nothing here may read data/ground_truth/.
"""
