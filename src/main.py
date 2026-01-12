import math
import random

from neo4j import GraphDatabase

import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import plotly.express as px

# color palette
COLORS = px.colors.qualitative.Plotly


# --------------------------------
# NEO4J CONFIG
# --------------------------------
NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "test1234")
driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

# --------------------------------
# MAP PARAMETERS
# --------------------------------
HEX_RADIUS = 1.0
MAP_RADIUS = 4
PRIORITY_CLUSTERS = 3     # number of high-priority regions
MAX_PRIORITY = 5

# --------------------------------
# HEX GRID
# --------------------------------
def axial_to_cart(q, r, size):
    x = size * (3/2 * q)
    y = size * (math.sqrt(3) * (r + q/2))
    return x, y

def generate_hex_grid(radius):
    hexes = []
    for q in range(-radius, radius + 1):
        r1 = max(-radius, -q - radius)
        r2 = min(radius, -q + radius)
        for r in range(r1, r2 + 1):
            hexes.append((q, r))
    return hexes

HEXES = generate_hex_grid(MAP_RADIUS)

# --------------------------------
# PRIORITY GENERATION (CLUSTERED)
# --------------------------------
def generate_clustered_priorities(hexes, n_clusters):
    centers = random.sample(hexes, n_clusters)

    priorities = {}
    for q, r in hexes:
        min_dist = min(abs(q - cq) + abs(r - cr) for cq, cr in centers)
        base = max(MAX_PRIORITY - min_dist, 1)
        noise = random.choice([0, 0, 1])  # mild randomness
        priorities[(q, r)] = min(base + noise, MAX_PRIORITY)

    return priorities

# --------------------------------
# NEO4J GRAPH OPS
# --------------------------------
def reset_db(tx):
    tx.run("MATCH (n) DETACH DELETE n")

def create_hexes(tx):
    priorities = generate_clustered_priorities(HEXES, PRIORITY_CLUSTERS)
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
            priority=priorities[(q, r)]
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

# --------------------------------
# FIGURES
# --------------------------------
def priority_map_figure(hexes):
    xs, ys, ps = [], [], []
    for h in hexes:
        x, y = axial_to_cart(h["q"], h["r"], HEX_RADIUS)
        xs.append(x)
        ys.append(y)
        ps.append(h["p"])

    fig = go.Figure(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers",
            marker=dict(
                size=18,
                symbol="hexagon",
                color=ps,
                colorscale="Viridis",
                colorbar=dict(title="Priority"),
            ),
            text=[f"Priority {p}" for p in ps],
        )
    )

    fig.update_layout(
        title="Hex Map – Clustered Priority Regions",
        xaxis=dict(scaleanchor="y", visible=False),
        yaxis=dict(visible=False),
        height=700,
    )
    return fig

# -------------------------------
# routing helpers & annotations
# -------------------------------
def _euclidean(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _nearest_neighbor_order(points, priority_weight=0.6):
    """Return points ordered by a nearest-neighbor heuristic that favors priority.

    - points: list of dicts with keys 'hid','x','y','p' (priority)
    - priority_weight: how strongly to prefer higher priority (larger => more preference)

    Start deterministically at the point with highest priority (tie-breaker: lowest hid).
    When selecting next point, choose by minimizing (distance - priority_weight * priority).
    """
    if not points:
        return []
    pts = points.copy()
    # start at highest-priority (tie-breaker lowest hid)
    start = max(pts, key=lambda p: (p.get("p", 0), -p["hid"]))
    ordered = [start]
    pts.remove(start)
    while pts:
        last = ordered[-1]
        def score(p):
            dist = _euclidean((last["x"], last["y"]), (p["x"], p["y"]))
            prio = p.get("p", 0)
            return dist - priority_weight * prio
        nxt = min(pts, key=score)
        pts.remove(nxt)
        ordered.append(nxt)
    return ordered

# Arrow annotations removed: directional arrows disabled to avoid overlapping straight shafts with smoothed lines


def assignment_figure(data):
    fig = go.Figure()
    uavs = sorted(set(d["uav"] for d in data))

    for idx, uav in enumerate(uavs):
        pts_raw = [d for d in data if d["uav"] == uav]
        pts = []
        for d in pts_raw:
            x, y = axial_to_cart(d["q"], d["r"], HEX_RADIUS)
            pts.append({"hid": d["hid"], "x": x, "y": y, "q": d["q"], "r": d["r"], "p": d.get("p", 0)})

        if not pts:
            continue

        ordered = _nearest_neighbor_order(pts)
        xs = [p["x"] for p in ordered]
        ys = [p["y"] for p in ordered]

        color = COLORS[idx % len(COLORS)] if COLORS else None

        # Draw smoothed path with markers
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines+markers",
                name=f"UAV {uav}",
                marker=dict(size=18, symbol="hexagon", color=color),
                line=dict(width=2, shape='spline', smoothing=1.3, color=color),
            )
        )

        # Numeric order labels
        labels = [str(i + 1) for i in range(len(xs))]
        # include priority in hovertext for clarity
        hover = [f"#{p['hid']} (prio {p.get('p', 0)})" for p in ordered]
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="text",
                text=labels,
                textposition="top center",
                showlegend=False,
                textfont=dict(size=12, color="black"),
                hovertext=hover,
                hoverinfo="text",
            )
        )


    fig.update_layout(
        title="Coverage Assignment Result",
        xaxis=dict(scaleanchor="y", visible=False),
        yaxis=dict(visible=False),
        height=700,
    )
    return fig

# --------------------------------
# DASH APP
# --------------------------------
app = dash.Dash(__name__)

app.layout = html.Div(
    [
        html.H2("UAV Swarm Coverage Planning (Offline)"),

        html.Div(
            [
                html.H4("Map View"),
                dcc.Graph(id="map"),
            ],
            style={"width": "100%", "display": "block"},
        ),

        html.Label("Number of UAVs"),
        dcc.Slider(
            id="uav-slider",
            min=1,
            max=10,
            step=1,
            value=3,
            marks={i: str(i) for i in range(1, 11)},
        ),

        html.Div(
            [
                html.Button("Restart", id="reset-btn", n_clicks=0),

                dcc.RadioItems(
                    id="view-toggle",
                    options=[
                        {"label": "Assignment", "value": "assignment"},
                        {"label": "Original", "value": "original"},
                    ],
                    value="assignment",
                    style={"display": "inline-block", "marginLeft": "20px"},
                ),

                # store the original priority map and last assignment so toggle can display them reliably
                dcc.Store(id="orig-map", data=None),
                dcc.Store(id="last-assignment", data=None),

            ],
            style={"marginTop": "15px"},
        ),
    ],
    style={"maxWidth": "1100px", "margin": "0 auto"},
)

@app.callback(
    Output("map", "figure"),
    Output("orig-map", "data"),
    Output("last-assignment", "data"),
    Output("view-toggle", "value"),
    Input("uav-slider", "value"),
    Input("reset-btn", "n_clicks"),
    Input("view-toggle", "value"),
    State("map", "figure"),
    State("orig-map", "data"),
    State("last-assignment", "data"),
)
def update_map(n_uavs, reset_clicks, view_toggle, current_map_fig, orig_map_data, last_assignment):
    ctx = dash.callback_context

    trigger = None
    if ctx.triggered:
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    # Initial or reset -> recreate the hexes and store & show priority map; clear last_assignment
    if not ctx.triggered or trigger == "reset-btn":
        with driver.session() as s:
            s.execute_write(reset_db)
            s.execute_write(create_hexes)
            orig_fig = priority_map_figure(fetch_hexes())
        # force view-toggle to 'original' on reset
        return orig_fig, orig_fig, None, "original"

    # Slider changed -> recompute assignment and store it (do not overwrite original)
    if trigger == "uav-slider":
        with driver.session() as s:
            s.execute_write(create_uavs, n_uavs)
            s.execute_write(assign_hexes)
            assign_fig = assignment_figure(fetch_assignments())

        # always update the last-assignment store
        if view_toggle == "original":
            # user is viewing original — keep displayed map unchanged, but save new assignment
            return dash.no_update, orig_map_data, assign_fig, dash.no_update

        # otherwise show assignment and save it
        return assign_fig, orig_map_data, assign_fig, dash.no_update

    # View toggle changed -> switch to original or assignment (use stored last-assignment)
    if trigger == "view-toggle":
        if view_toggle == "original":
            if orig_map_data is not None:
                return orig_map_data, orig_map_data, last_assignment, dash.no_update
            with driver.session() as s:
                s.execute_write(reset_db)
                s.execute_write(create_hexes)
                orig_fig = priority_map_figure(fetch_hexes())
            return orig_fig, orig_fig, last_assignment, dash.no_update

        # view_toggle == 'assignment'
        if last_assignment is not None:
            return last_assignment, orig_map_data, last_assignment, dash.no_update
        # if no stored assignment, compute one now
        with driver.session() as s:
            s.execute_write(create_uavs, n_uavs)
            s.execute_write(assign_hexes)
            assign_fig = assignment_figure(fetch_assignments())
        return assign_fig, orig_map_data, assign_fig, dash.no_update

    return dash.no_update, orig_map_data, last_assignment, dash.no_update

# --------------------------------
# ENTRY POINT
# --------------------------------
if __name__ == "__main__":
    app.run(debug=True)
