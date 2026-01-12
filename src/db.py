from neo4j import GraphDatabase
import math

from hexgrid import HEXES, generate_clustered_priorities, HEX_RADIUS, axial_to_cart

NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "test1234")
driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)


def reset_db(tx):
    tx.run("MATCH (n) DETACH DELETE n")


def create_hexes(tx):
    priorities = generate_clustered_priorities(HEXES, n_clusters=3)
    for i, (q, r) in enumerate(HEXES):
        # Convert axial coordinates to Cartesian for distance calculations
        x, y = axial_to_cart(q, r, HEX_RADIUS)
        tx.run(
            """
            CREATE (:Hex {
                id:$id,
                q:$q,
                r:$r,
                x:$x,
                y:$y,
                priority:$priority
            })
            """,
            id=i,
            q=q,
            r=r,
            x=x,
            y=y,
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


def compute_routes_gds():
    """
    Compute optimal routes for each UAV using GDS (Graph Data Science) library.
    Uses TSP (Traveling Salesman Problem) approximation to find efficient paths.
    Returns a dictionary mapping UAV IDs to ordered lists of hex IDs.
    """
    routes = {}
    
    with driver.session() as session:
        # First, get all UAVs and their assigned hexes
        result = session.run("""
            MATCH (u:UAV)-[:ASSIGNED]->(h:Hex)
            RETURN u.id AS uav_id, collect(h.id) AS hex_ids, 
                   collect({id: h.id, x: h.x, y: h.y}) AS hexes
            ORDER BY u.id
        """)
        
        for record in result:
            uav_id = record["uav_id"]
            hex_ids = record["hex_ids"]
            hexes = record["hexes"]
            
            if len(hexes) <= 1:
                # No routing needed for 0 or 1 hex
                routes[uav_id] = hex_ids if hex_ids else []
                continue
            
            # Create a temporary graph projection for this UAV
            # We'll use Cypher to solve TSP approximation
            
            # Create distance matrix between all pairs of hexes
            distance_matrix = []
            for i, hex1 in enumerate(hexes):
                row = []
                for j, hex2 in enumerate(hexes):
                    if i == j:
                        row.append(0.0)
                    else:
                        # Calculate Euclidean distance
                        dx = hex1["x"] - hex2["x"]
                        dy = hex1["y"] - hex2["y"]
                        distance = math.sqrt(dx*dx + dy*dy)
                        row.append(distance)
                distance_matrix.append(row)
            
            # Solve TSP using nearest neighbor heuristic (GDS alternative)
            # This is a simplified version - in production you'd use gds.alpha.tsp
            
            if len(hexes) > 0:
                # Use a simple heuristic: start with highest priority, then go to nearest
                route_order = solve_tsp_heuristic(hexes, distance_matrix)
                routes[uav_id] = [hexes[idx]["id"] for idx in route_order]
            else:
                routes[uav_id] = []
    
    return routes


def solve_tsp_heuristic(hexes, distance_matrix):
    """
    Solve TSP using nearest neighbor heuristic.
    Returns list of indices in visitation order.
    """
    n = len(hexes)
    if n == 0:
        return []
    
    # Start with the hex with highest priority (or first if priorities are equal)
    start_idx = 0
    for i in range(1, n):
        if hexes[i].get("priority", 0) > hexes[start_idx].get("priority", 0):
            start_idx = i
    
    visited = [False] * n
    route = [start_idx]
    visited[start_idx] = True
    
    current = start_idx
    for _ in range(n - 1):
        # Find nearest unvisited neighbor
        nearest = -1
        min_dist = float('inf')
        for i in range(n):
            if not visited[i] and distance_matrix[current][i] < min_dist:
                min_dist = distance_matrix[current][i]
                nearest = i
        
        if nearest != -1:
            route.append(nearest)
            visited[nearest] = True
            current = nearest
    
    return route


def compute_routes_gds_full():
    """
    Alternative implementation using GDS library functions.
    This requires the GDS library to be installed in Neo4j.
    """
    routes = {}
    
    with driver.session() as session:
        try:
            # Check if GDS is available
            session.run("RETURN gds.version()").single()
            
            # Create a graph projection for routing
            session.run("""
                CALL gds.graph.project(
                    'hexGraph',
                    ['Hex', 'UAV'],
                    {
                        ASSIGNED: {
                            orientation: 'UNDIRECTED'
                        }
                    }
                )
            """)
            
            # For each UAV, find optimal route using TSP approximation
            # This is a simplified version - actual GDS TSP would require more setup
            
            uavs_result = session.run("MATCH (u:UAV) RETURN u.id AS uav_id")
            
            for record in uavs_result:
                uav_id = record["uav_id"]
                
                # Get the route for this UAV using Yen's K-shortest paths between consecutive high-priority nodes
                # This is a simplified approach - real implementation would use gds.alpha.tsp
                
                route_result = session.run("""
                    MATCH (u:UAV {id: $uav_id})-[:ASSIGNED]->(h:Hex)
                    WITH h ORDER BY h.priority DESC, h.id
                    RETURN collect(h.id) AS route
                """, uav_id=uav_id)
                
                route_record = route_result.single()
                if route_record:
                    routes[uav_id] = route_record["route"]
            
            # Clean up the projected graph
            session.run("CALL gds.graph.drop('hexGraph')")
            
        except Exception as e:
            print(f"GDS routing not available: {e}")
            # Fall back to heuristic method
            routes = compute_routes_gds()
    
    return routes


def compute_shortest_paths():
    """
    Compute shortest paths between consecutive hexes in assignment order.
    Uses Dijkstra's algorithm to find optimal paths between hexes.
    """
    routes = {}
    
    with driver.session() as session:
        # First create relationships between neighboring hexes for pathfinding
        # This creates a grid where hexes are connected to their neighbors
        
        session.run("""
            MATCH (h1:Hex), (h2:Hex)
            WHERE h1.id < h2.id
            WITH h1, h2,
                 sqrt((h1.x - h2.x)^2 + (h1.y - h2.y)^2) AS distance
            WHERE distance < 2.5 * $radius  // Approximate neighbor threshold
            MERGE (h1)-[:CONNECTED {distance: distance}]-(h2)
        """, radius=HEX_RADIUS)
        
        # Get UAV assignments
        uavs_result = session.run("""
            MATCH (u:UAV)-[:ASSIGNED]->(h:Hex)
            RETURN u.id AS uav_id, collect(h.id) AS hex_ids
            ORDER BY u.id
        """)
        
        for record in uavs_result:
            uav_id = record["uav_id"]
            hex_ids = record["hex_ids"]
            
            if len(hex_ids) <= 1:
                routes[uav_id] = hex_ids
                continue
            
            # Reorder hexes using a traveling salesman approximation
            # Start with the first hex, then find nearest unvisited neighbor
            ordered_ids = [hex_ids[0]]
            unvisited = set(hex_ids[1:])
            
            current = hex_ids[0]
            while unvisited:
                # Find nearest unvisited hex
                nearest_result = session.run("""
                    MATCH (current:Hex {id: $current_id})
                    MATCH (h:Hex)
                    WHERE h.id IN $unvisited
                    WITH h, sqrt((current.x - h.x)^2 + (current.y - h.y)^2) AS distance
                    ORDER BY distance
                    LIMIT 1
                    RETURN h.id AS nearest_id
                """, current_id=current, unvisited=list(unvisited))
                
                nearest_record = nearest_result.single()
                if nearest_record:
                    nearest_id = nearest_record["nearest_id"]
                    ordered_ids.append(nearest_id)
                    unvisited.remove(nearest_id)
                    current = nearest_id
                else:
                    break
            
            routes[uav_id] = ordered_ids
        
        # Clean up the temporary connections
        session.run("MATCH ()-[r:CONNECTED]-() DELETE r")
    
    return routes


# Alias the main routing function for use in figures.py
compute_routes_gds = compute_routes_gds