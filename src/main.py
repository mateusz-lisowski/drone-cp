"""Example CLI for coverage path planner.

Usage: run `python -m src.main` from project root to see example output.
"""
import argparse
from typing import List, Tuple
from coverage import generate_coverage_path
from visualize import plot_coverage

LatLon = Tuple[float, float]


def example(polygon: List[LatLon], spacing: float, samples: int, plot: bool, out: str | None):
    waypoints = generate_coverage_path(polygon, spacing_m=spacing, angle_samples=samples)
    print("Generated {} waypoints:".format(len(waypoints)))
    for lat, lon in waypoints:
        print(f"{lat:.6f},{lon:.6f}")

    if plot:
        # save to out if provided
        _ = plot_coverage(polygon, waypoints, coords_are_merc=False, show=False if out else True, save_path=out)


def main():
    parser = argparse.ArgumentParser(description="Coverage path planner example")
    parser.add_argument("--plot", action="store_true", help="Show/save a plot of the coverage path")
    parser.add_argument("--out", type=str, default=None, help="Path to save plot (PNG). If omitted and --plot is set, shows plot interactively.")
    parser.add_argument("--spacing", type=float, default=10.0, help="Sweep spacing (m)")
    parser.add_argument("--samples", type=int, default=36, help="Angle sample count")
    args = parser.parse_args()

    polygon: List[LatLon] = [
        (37.7749, -122.4194),
        (37.7749, -122.4184),
        (37.7740, -122.4184),
        (37.7740, -122.4194),
        (37.7741, -122.4196),
    ]
    example(polygon, spacing=args.spacing, samples=args.samples, plot=args.plot, out=args.out)


if __name__ == "__main__":
    main()
