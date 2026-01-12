from neo4j import GraphDatabase

from hexgrid import HEXES, generate_clustered_priorities

NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "test1234")
driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)


def reset_db(tx):
    tx.run("MATCH (n) DETACH DELETE n")


def create_hexes(tx):
    priorities = generate_clustered_priorities(HEXES, n_clusters=3)
    for i, (q, r) in enumerate(HEXES):
        tx.run(
            """
            CREATE (:Hex {
                id:$id,
                q:$q,
                r:$r,
                priority:$priority
            })
            """,
            id=i,
            q=q,
            r=r,
            priority=priorities[(q, r)],
        )


def create_uavs(tx, n):
    # Remove existing UAV nodes to avoid duplicates when re-creating
    tx.run("MATCH (u:UAV) DETACH DELETE u")
    for i in range(n):
        tx.run("CREATE (:UAV {id:$id})", id=i)


def assign_hexes(tx):
    # Remove previous assignment relationships to avoid accumulating duplicates
    tx.run("MATCH ()-[r:ASSIGNED]->() DELETE r")
    tx.run(
        """
        MATCH (h:Hex)
        WITH h ORDER BY h.priority DESC
        MATCH (u:UAV)
        WITH h, collect(u) AS uavs
        WITH h, uavs[h.id % size(uavs)] AS uav
        CREATE (uav)-[:ASSIGNED]->(h)
        """
    )


def fetch_hexes():
    q = """
    MATCH (h:Hex)
    RETURN h.id AS id, h.q AS q, h.r AS r, h.priority AS p
    """
    with driver.session() as s:
        return s.run(q).data()


def fetch_assignments():
    q = """
    MATCH (u:UAV)-[:ASSIGNED]->(h:Hex)
    RETURN u.id AS uav, h.id AS hid, h.q AS q, h.r AS r, h.priority AS p
    ORDER BY u.id, h.id
    """
    with driver.session() as s:
        return s.run(q).data()
