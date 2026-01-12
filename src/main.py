import dash
from dash import dcc, html, Input, Output, State

# import behaviour from smaller modules
from db import (
    driver,
    reset_db,
    create_hexes,
    create_uavs,
    assign_hexes,
    fetch_hexes,
    fetch_assignments,
)
from figures import priority_map_figure, assignment_figure


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
