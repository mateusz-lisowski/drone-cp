"""Minimal coverage path planner.

Input: polygon as list of (lat, lon) tuples (degrees).
Output: ordered list of (lat, lon) waypoints covering polygon with boustrophedon sweep.

Depends on: shapely, pyproj
"""
from typing import List, Tuple, Iterable, Optional

from shapely.geometry import Polygon, LineString, MultiLineString
from shapely.affinity import rotate

from pyproj import Transformer

LatLon = Tuple[float, float]

# Use Web Mercator (EPSG:3857) for local meter coordinates - good enough for small areas
_WGS84_TO_MERC = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
_MERC_TO_WGS84 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)


def _to_xy(coords: Iterable[LatLon]) -> List[Tuple[float, float]]:
    xs, ys = _WGS84_TO_MERC.transform(
        [c[1] for c in coords],  # lon
        [c[0] for c in coords],  # lat
    )
    return list(zip(xs, ys))


def _to_latlon(xs: Iterable[float], ys: Iterable[float]) -> List[LatLon]:
    lons, lats = _MERC_TO_WGS84.transform(list(xs), list(ys))
    return list(zip(lats, lons))


def _line_segments_from_intersection(inter) -> List[LineString]:
    if inter.is_empty:
        return []
    if isinstance(inter, LineString):
        return [inter]
    if isinstance(inter, MultiLineString):
        return list(inter.geoms)
    # If we get a Point or other geometry, ignore (degenerate intersection)
    return []


def _segments_endpoints(segments: List[LineString]) -> List[Tuple[float, float]]:
    pts = []
    for seg in segments:
        x0, y0 = seg.coords[0]
        x1, y1 = seg.coords[-1]
        pts.append((x0, y0))
        pts.append((x1, y1))
    return pts


def _path_length(points: List[Tuple[float, float]]) -> float:
    total = 0.0
    for i in range(1, len(points)):
        dx = points[i][0] - points[i - 1][0]
        dy = points[i][1] - points[i - 1][1]
        total += (dx * dx + dy * dy) ** 0.5
    return total


def generate_coverage_path(
    polygon_latlon: List[LatLon],
    spacing_m: float = 20.0,
    angle_samples: int = 36,
    return_merc: bool = False,
) -> List[LatLon]:
    """Generate a boustrophedon coverage path for the polygon.

    Args:
        polygon_latlon: list of (lat, lon) vertices (degrees, WGS84)
        spacing_m: distance between adjacent sweep lines in meters
        angle_samples: number of angles to sample between 0 and 180 degrees
        return_merc: if True, returns waypoints in mercator (x,y) meters instead of lat/lon

    Returns:
        list of ordered (lat, lon) waypoints in degrees (unless return_merc True)
    """
    if len(polygon_latlon) < 3:
        raise ValueError("Polygon must have at least 3 vertices")

    # Project to metric coordinates
    xy = _to_xy(polygon_latlon)
    poly = Polygon(xy)
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        raise ValueError("Polygon is empty after projection")

    best_path: Optional[List[Tuple[float, float]]] = None
    best_len = float("inf")

    # Sample angles from 0 to 180
    for i in range(angle_samples):
        angle = (180.0 * i) / angle_samples

        # Rotate polygon so sweep lines are vertical (x const)
        rpoly = rotate(poly, -angle, origin="centroid", use_radians=False)
        minx, miny, maxx, maxy = rpoly.bounds

        # Generate vertical sweep lines across bounding box
        xs = []
        x = minx - spacing_m  # start a bit before to ensure full coverage
        while x <= maxx + spacing_m:
            xs.append(x)
            x += spacing_m

        strips: List[List[Tuple[float, float]]] = []

        for j, x in enumerate(xs):
            line = LineString([(x, miny - spacing_m), (x, maxy + spacing_m)])
            inter = rpoly.intersection(line)
            segs = _line_segments_from_intersection(inter)
            # Collect segment endpoints (ordered along y)
            pts_this_strip: List[Tuple[float, float]] = []
            for seg in segs:
                x0, y0 = seg.coords[0]
                x1, y1 = seg.coords[-1]
                # order segment points from top to bottom (y desc)
                if y0 > y1:
                    pts_this_strip.append((x0, y0))
                    pts_this_strip.append((x1, y1))
                else:
                    pts_this_strip.append((x1, y1))
                    pts_this_strip.append((x0, y0))
            # If multiple segments on this line, sort by mean y to place them in sweep order
            if pts_this_strip:
                # Group point pairs into segments and sort by midpoint y
                seg_pairs = [pts_this_strip[k : k + 2] for k in range(0, len(pts_this_strip), 2)]
                seg_pairs.sort(key=lambda s: -((s[0][1] + s[1][1]) / 2.0))  # top->bottom
                # Flatten
                flat = [pt for pair in seg_pairs for pt in pair]
                # Reverse every other strip to create boustrophedon
                if len(strips) % 2 == 1:
                    flat.reverse()
                strips.append(flat)

        # Flatten strips into candidate path in rotated frame
        candidate: List[Tuple[float, float]] = []
        for s in strips:
            if not s:
                continue
            candidate.extend(s)

        # Rotate candidate back to original frame
        if not candidate:
            continue
        cand_ls = LineString(candidate)
        cand_orig = rotate(cand_ls, angle, origin=(poly.centroid.x, poly.centroid.y), use_radians=False)
        cand_points = list(cand_orig.coords)

        length = _path_length(cand_points)
        if length < best_len:
            best_len = length
            best_path = cand_points

    if best_path is None:
        raise RuntimeError("Failed to compute a coverage path")

    if return_merc:
        return best_path  # type: ignore

    xs, ys = zip(*best_path)
    latlon = _to_latlon(xs, ys)
    return latlon


if __name__ == "__main__":
    # Simple quick test when run directly
    square = [(37.7749, -122.4194), (37.7749, -122.4184), (37.7740, -122.4184), (37.7740, -122.4194)]
    wps = generate_coverage_path(square, spacing_m=10.0, angle_samples=36)
    for lat, lon in wps:
        print(f"{lat:.6f}, {lon:.6f}")
