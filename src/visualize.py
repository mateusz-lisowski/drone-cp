"""Visualization helpers for coverage paths.

Provides plot_coverage(...) which draws the polygon and the ordered
waypoints using Matplotlib. Inputs may be WGS84 lat/lon tuples or
Mercator (x,y) meter coordinates.
"""
from typing import List, Tuple, Optional
from pyproj import Transformer
from shapely.geometry import Polygon
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
import tempfile
import os

LatLon = Tuple[float, float]

_WGS84_TO_MERC = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
_MERC_TO_WGS84 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)


def _to_xy(coords: List[LatLon]) -> List[tuple]:
    xs, ys = _WGS84_TO_MERC.transform([c[1] for c in coords], [c[0] for c in coords])
    return list(zip(xs, ys))


def plot_coverage(
    polygon_latlon: List[LatLon],
    waypoints: List[LatLon],
    coords_are_merc: bool = False,
    show: bool = False,
    save_path: Optional[str] = None,
    ax=None,
):
    """Plot polygon and coverage waypoints.

    Args:
        polygon_latlon: polygon vertices as (lat, lon) or (x,y) if coords_are_merc
        waypoints: ordered waypoints as (lat, lon) or (x,y)
        coords_are_merc: if True, treat inputs as mercator (meters)
        show: if True, call plt.show()
        save_path: if given, save figure to path
        ax: optional Matplotlib Axes to draw into

    Returns:
        (fig, ax)
    """
    if coords_are_merc:
        poly_xy = polygon_latlon
        wps_xy = waypoints
    else:
        poly_xy = _to_xy(polygon_latlon)
        wps_xy = _to_xy(waypoints) if waypoints else []

    poly = Polygon(poly_xy)
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 6))
    else:
        fig = ax.figure

    patch = MplPolygon(list(poly.exterior.coords), closed=True, facecolor="lightgray", edgecolor="k", alpha=0.5)
    ax.add_patch(patch)
    for interior in poly.interiors:
        hole = MplPolygon(list(interior.coords), closed=True, facecolor="white", edgecolor="k")
        ax.add_patch(hole)

    if wps_xy:
        xs, ys = zip(*wps_xy)
        ax.plot(xs, ys, "-o", color="C1", markersize=3, linewidth=0.8)

    ax.set_aspect("equal", adjustable="datalim")
    ax.autoscale()
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")

    saved_path = None

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        saved_path = save_path

    if show:
        backend = matplotlib.get_backend().lower()
        non_interactive = (
            backend == "agg"
            or "inline" in backend
            or backend.startswith("module://")
            or backend in ("pdf", "ps", "svg")
        )
        if non_interactive:
            # No interactive display available; if we didn't already save, write to temp file
            if saved_path is None:
                fd, tmp = tempfile.mkstemp(suffix=".png", prefix="coverage_")
                os.close(fd)
                fig.savefig(tmp, dpi=150, bbox_inches="tight")
                saved_path = tmp
                print(f"No interactive display available; saved plot to {tmp}")
            else:
                print(f"No interactive display available; saved plot to {saved_path}")
        else:
            plt.show()

    return fig, ax, saved_path
