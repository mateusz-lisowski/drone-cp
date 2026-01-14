# Drone CP

Coverage path planner for UAVs build with Python and Neo4J.

---

The routing algorithm solves a Traveling Salesman Problem (TSP) for each UAV to determine optimal visitation order of assigned hexes. Since TSP is NP-hard, it employs efficient heuristics for near-optimal solutions rather than exhaustive search.

**Core Approach: Nearest Neighbor Heuristic**
The algorithm uses a greedy nearest neighbor approach. For each UAV, it starts at the highest-priority hex (ensuring critical areas are covered first), then repeatedly moves to the closest unvisited hex until all assigned hexes are visited. This creates a route that minimizes travel distance incrementally at each step.

**Implementation Steps:**
1. **Data Collection**: Gather all hexes assigned to a UAV with their Cartesian coordinates (x, y) and priority values.
2. **Distance Matrix Creation**: Calculate Euclidean distances between all hex pairs (O(n²) complexity).
3. **Route Construction**: Apply nearest neighbor algorithm - start at highest-priority hex, find closest unvisited neighbor, move there, repeat until all visited.
4. **Route Optimization**: The algorithm produces ordered lists of hex IDs representing visitation sequence.

**Key Characteristics:**
- **Time Complexity**: O(n²) per UAV where n = hexes per UAV
- **Approximation Quality**: Typically 1.25× to 1.5× optimal distance
- **Starting Strategy**: Begins at highest-priority hex for critical coverage
- **Distance Metric**: Uses Euclidean distance (straight-line) between hex centers

**Algorithm Strengths:**
- **Simplicity**: Easy to implement and understand
- **Speed**: Fast computation suitable for interactive applications
- **Priority Awareness**: Naturally covers high-value areas first
- **Visual Effectiveness**: Produces reasonable routes for demonstration purposes

**Limitations:**
- **Suboptimal**: No guarantee of optimal routes (NP-hard problem)
- **Local Minima**: Can get trapped in poor routes due to greedy decisions
- **Starting Sensitivity**: Route quality depends heavily on starting point choice
- **Independent Processing**: Processes each UAV separately without coordination

**Alternative Approaches Considered:**
1. **Priority-Only Ordering**: Simple sort by priority (ignores distances)
2. **Christofides Algorithm**: Better approximation (1.5× optimal) but more complex
3. **Genetic Algorithms**: Near-optimal but slower, better for offline planning
4. **GDS Library Methods**: Neo4j Graph Data Science algorithms for production use

**Extension Opportunities:**
The current algorithm serves as a foundation that could be extended with:
- Dynamic re-routing for real-time adjustments
- Battery life constraints and no-fly zones
- Multi-UAV coordination to avoid conflicts
- Time-window constraints for time-sensitive missions

**Design Philosophy:**
The algorithm prioritizes clarity and interactivity over absolute optimality. It demonstrates fundamental routing concepts while remaining computationally efficient for demonstration purposes. The implementation balances solution quality with execution speed, acknowledging that perfect solutions are computationally prohibitive for real-time applications.

**Key Insight:**
The algorithm embodies the classic engineering trade-off: "Better a good solution now than a perfect solution too late." For UAV coverage planning where priorities may change and conditions evolve, a fast, good-enough routing algorithm that can replan quickly often outperforms a slower, optimal algorithm in practical scenarios.

The system's modular design allows easy swapping of routing algorithms, enabling future upgrades to more sophisticated methods while maintaining the same visualization and assignment infrastructure.