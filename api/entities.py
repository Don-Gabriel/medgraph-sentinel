"""Generic node inspector for the console's drill-down side panel
(INTERFACES §6: GET /api/v1/entities/{id})."""
from fastapi import APIRouter, Depends, HTTPException

from api.graph import (display_label, get_session, label_and_key_for,
                       run_query, to_jsonable)

router = APIRouter(prefix="/api/v1")

# The label is interpolated from the fixed prefix map (never from user
# input), so each lookup hits that label's unique-id index instead of
# scanning the store. count(x) over the OPTIONAL MATCH is the node degree —
# all relationship types, IMPLICATES included, since this is a raw inspector.
Q_ENTITY = """\
MATCH (n:{label} {{{key}: $id}})
OPTIONAL MATCH (n)--(x)
RETURN labels(n)[0] AS type, properties(n) AS props, count(x) AS degree
"""


@router.get("/entities/{entity_id}")
def entity_detail(entity_id: str, session=Depends(get_session)) -> dict:
    routed = label_and_key_for(entity_id)
    if routed is None:  # id matches no label's prefix scheme — nothing to scan
        raise HTTPException(status_code=404, detail=f"unknown entity {entity_id}")
    label, key = routed
    rows = run_query(session, Q_ENTITY.format(label=label, key=key), id=entity_id)
    if not rows:
        raise HTTPException(status_code=404, detail=f"unknown entity {entity_id}")
    row = rows[0]
    props = to_jsonable(row["props"])
    return {"id": entity_id, "type": row["type"],
            "label": display_label(props, entity_id),
            "props": props, "degree": row["degree"]}
