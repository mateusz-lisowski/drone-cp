import plotly.graph_objects as go
import plotly.express as px

from hexgrid import axial_to_cart, HEX_RADIUS
from routing import _nearest_neighbor_order

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
