import plotly.graph_objects as go
import plotly.express as px

from hexgrid import axial_to_cart, HEX_RADIUS
from db import compute_routes_gds

COLORS = px.colors.qualitative.Plotly


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
# Assignment plotting
# -------------------------------

def assignment_figure(data):
    fig = go.Figure()
    uavs = sorted(set(d["uav"] for d in data))

    # index assigned hexes by UAV and hid for quick lookup
    by_uav = {}
    for d in data:
        by_uav.setdefault(d["uav"], {})[d["hid"]] = d

    # attempt to compute routes via GDS; fallback to deterministic priority ordering
    try:
        routes = compute_routes_gds()
    except Exception as e:
        print(f"GDS routing call failed: {e}")
        routes = {}

    for idx, uav in enumerate(uavs):
        ordered_rows = []

        if uav in routes and routes[uav]:
            # map route hex ids to the original rows (skip missing ids)
            ordered_rows = [by_uav[uav].get(hid) for hid in routes[uav] if by_uav[uav].get(hid)]
        else:
            # deterministic fallback: sort by priority desc then hid
            ordered_rows = sorted([d for d in data if d["uav"] == uav], key=lambda x: (-x.get("p", 0), x["hid"]))

        if not ordered_rows:
            continue

        xs = []
        ys = []
        ordered = []
        for d in ordered_rows:
            x, y = axial_to_cart(d["q"], d["r"], HEX_RADIUS)
            xs.append(x)
            ys.append(y)
            ordered.append({"hid": d["hid"], "x": x, "y": y, "p": d.get("p", 0)})

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
