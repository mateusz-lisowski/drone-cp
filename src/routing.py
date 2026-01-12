import math


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
