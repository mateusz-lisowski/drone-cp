import math
import random

# Map and priority config
HEX_RADIUS = 1.0
MAP_RADIUS = 4
PRIORITY_CLUSTERS = 3     # number of high-priority regions
MAX_PRIORITY = 5


def axial_to_cart(q, r, size):
    x = size * (3 / 2 * q)
    y = size * (math.sqrt(3) * (r + q / 2))
    return x, y


def generate_hex_grid(radius):
    hexes = []
    for q in range(-radius, radius + 1):
        r1 = max(-radius, -q - radius)
        r2 = min(radius, -q + radius)
        for r in range(r1, r2 + 1):
            hexes.append((q, r))
    return hexes


def generate_clustered_priorities(hexes, n_clusters):
    centers = random.sample(hexes, n_clusters)

    priorities = {}
    for q, r in hexes:
        min_dist = min(abs(q - cq) + abs(r - cr) for cq, cr in centers)
        base = max(MAX_PRIORITY - min_dist, 1)
        noise = random.choice([0, 0, 1])  # mild randomness
        priorities[(q, r)] = min(base + noise, MAX_PRIORITY)

    return priorities


# Precompute the grid used by the app
HEXES = generate_hex_grid(MAP_RADIUS)
