"""Simple Neo4j client wrapper for coverage planning.

This module provides a thin wrapper around the official `neo4j` driver
suitable for small demos and integration tests. It intentionally keeps
things simple: create nodes for `Waypoint` and `UAV`, and `ASSIGNED` relations.
"""
from neo4j import GraphDatabase, Driver


class Neo4jClient:
    def __init__(self, uri: str = "bolt://localhost:7687", user: str = "neo4j", password: str = "test"):
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    def clear(self) -> None:
        """Clear the whole graph (useful for tests/demos)."""
        with self._driver.session() as s:
            s.run("MATCH (n) DETACH DELETE n")

    def create_waypoint(self, wp_id: str, lat: float, lon: float) -> None:
        with self._driver.session() as s:
            s.run(
                "MERGE (w:Waypoint {id:$id}) SET w.lat=$lat, w.lon=$lon",
                id=wp_id,
                lat=lat,
                lon=lon,
            )

    def create_uav(self, uav_id: str) -> None:
        with self._driver.session() as s:
            s.run("MERGE (u:UAV {id:$id})", id=uav_id)

    def assign_uav_to_waypoint(self, uav_id: str, wp_id: str) -> None:
        with self._driver.session() as s:
            s.run(
                "MATCH (u:UAV {id:$uav_id}), (w:Waypoint {id:$wp_id}) MERGE (u)-[:ASSIGNED]->(w)",
                uav_id=uav_id,
                wp_id=wp_id,
            )

    def list_assignments(self):
        with self._driver.session() as s:
            res = s.run("MATCH (u:UAV)-[:ASSIGNED]->(w:Waypoint) RETURN u.id as uav, w.id as wp")
            return [record.data() for record in res]
