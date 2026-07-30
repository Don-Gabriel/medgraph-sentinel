"""Shared fixtures for the API tests: an in-process fake of the Neo4j
session, injected through the get_session dependency (api/graph.py).

The fake dispatches on the *exact query text* (whitespace-normalized) of
the module constants in api/alerts.py / api/entities.py. That is
deliberate: if an endpoint's Cypher changes, the fake misses and the test
fails loudly with the unknown query — the fake can never silently drift
away from the code under test.
"""
import pytest
from fastapi.testclient import TestClient


def _normalize(query: str) -> str:
    return " ".join(query.split())


class FakeRecord(dict):
    """neo4j Record look-alike: r["key"], dict(r), .get() — dict does all three."""


class FakeResult:
    def __init__(self, rows):
        self._rows = [FakeRecord(r) for r in rows]

    def __iter__(self):
        return iter(self._rows)

    def single(self):
        return self._rows[0] if self._rows else None


class FakeSession:
    """Register a handler (callable(params) -> list[dict], or a plain list)
    per query constant; .run() dispatches. Unknown query = test bug."""

    def __init__(self):
        self._handlers = {}

    def handle(self, query: str, handler):
        self._handlers[_normalize(query)] = handler

    def run(self, query: str, **params):
        handler = self._handlers.get(_normalize(query))
        if handler is None:
            raise AssertionError(f"FakeSession: no handler for query:\n{query}")
        rows = handler(params) if callable(handler) else handler
        return FakeResult(rows)


@pytest.fixture
def fake_session():
    return FakeSession()


@pytest.fixture
def client(fake_session):
    """TestClient with the Neo4j dependency overridden. No context manager:
    the lifespan (narration-cache check against the real driver) must not
    run in unit tests."""
    from api.graph import get_session
    from api.main import app

    app.dependency_overrides[get_session] = lambda: fake_session
    yield TestClient(app)
    app.dependency_overrides.clear()
