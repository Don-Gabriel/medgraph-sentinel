"""NOT IMPLEMENTED YET — M1 work item (see docs/STATUS.md NEXT 3).

Contract to implement (docs/INTERFACES.md section 4):
wait for Bolt (<=120s) -> apply graph/schema.cypher -> wipe -> load every
CSV from data/csv/ -> validate counts against data/manifest.json (mismatch =
non-zero exit with a diff) -> exit 0.
Bulk-load mechanism choice (LOAD CSV vs neo4j-admin import) is OQ #1 —
benchmark on the real dataset and record the numbers in DECISIONS.md.
"""
import sys

print(
    "loader: NOT IMPLEMENTED YET - see docs/INTERFACES.md section 4 and docs/STATUS.md",
    file=sys.stderr,
)
sys.exit(1)
