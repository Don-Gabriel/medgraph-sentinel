"""Entity inspector tests (INTERFACES §6: GET /api/v1/entities/{id}) —
prefix-to-label routing, Country's code key, label fallback, degree, 404s."""
from api.entities import Q_ENTITY
from api.graph import label_and_key_for

ENTITIES = {
    "CLI_000217": ("Clinic", "id",
                   {"id": "CLI_000217", "name": "Elysium Care Clinic",
                    "bed_count": 0}, 17),
    "PAT_000001": ("Patient", "id",
                   {"id": "PAT_000001", "full_name": "A. Fictional"}, 3),
    "ACC_000944": ("PaymentAccount", "id",
                   {"id": "ACC_000944", "bank_name": "First Fictional"}, 9),
    "TH": ("Country", "code", {"code": "TH", "name": "Thailand"}, 4021),
}


def install_entity_handlers(fake):
    for entity_id, (label, key, props, degree) in ENTITIES.items():
        def handler(params, label=label, props=props, degree=degree):
            if params["id"] != props.get("id", props.get("code")):
                return []
            return [{"type": label, "props": dict(props), "degree": degree}]
        fake.handle(Q_ENTITY.format(label=label, key=key), handler)
    # unknown-but-valid-prefix ids reach the database and find nothing
    fake.handle(Q_ENTITY.format(label="Doctor", key="id"), [])


def test_label_routing_covers_every_prefix_and_country():
    assert label_and_key_for("PAT_000001") == ("Patient", "id")
    assert label_and_key_for("ACC_000944") == ("PaymentAccount", "id")
    assert label_and_key_for("ALT_000001") == ("Alert", "id")
    assert label_and_key_for("TH") == ("Country", "code")
    assert label_and_key_for("XX_000001") is None   # no such prefix
    assert label_and_key_for("th") is None          # codes are upper-case


def test_entity_detail_and_label_fallbacks(client, fake_session):
    install_entity_handlers(fake_session)
    body = client.get("/api/v1/entities/CLI_000217").json()
    assert body == {"id": "CLI_000217", "type": "Clinic",
                    "label": "Elysium Care Clinic",
                    "props": {"id": "CLI_000217",
                              "name": "Elysium Care Clinic", "bed_count": 0},
                    "degree": 17}
    assert client.get("/api/v1/entities/PAT_000001").json()["label"] == "A. Fictional"
    assert client.get("/api/v1/entities/ACC_000944").json()["label"] == "ACC_000944"
    country = client.get("/api/v1/entities/TH").json()
    assert country["label"] == "Thailand" and country["degree"] == 4021


def test_entity_404s(client, fake_session):
    install_entity_handlers(fake_session)
    # valid prefix, no such node — hits the database, finds nothing
    response = client.get("/api/v1/entities/DOC_999999")
    assert response.status_code == 404
    assert response.json() == {"detail": "unknown entity DOC_999999"}
    # invalid prefix — rejected before any query runs
    assert client.get("/api/v1/entities/BOGUS_1").status_code == 404
