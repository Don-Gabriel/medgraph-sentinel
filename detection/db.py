"""One place for the Neo4j connection env contract (INTERFACES §1)."""
import os

from neo4j import GraphDatabase


def connect():
    return GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"),
              os.environ.get("NEO4J_PASSWORD", "")),
    )
