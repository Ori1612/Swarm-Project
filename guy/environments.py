"""
guy/environments.py

Single source of truth for all environment configurations and obstacle
placements used across the benchmarking and visualization modules.

Coordinates are taken verbatim from the "Master Environment Design
Specification" so that every module (server, gap test, stress test) shares
the exact same scientifically-controlled geometry.
"""

import numpy as np
from ori.environment import Environment

# NOTE: ori/obstacles/__init__.py is empty, so we import the primitives
# directly from their submodules (this keeps Ori's package untouched).
from ori.obstacles.box import Box
from ori.obstacles.sphere import Sphere
from ori.obstacles.cylinder import Cylinder
from ori.obstacles.plane import Plane
from ori.obstacles.half_sphere import HalfSphere


def build_cyber_city() -> Environment:
    """Configuration 1: 3D Visualization (The Cyber-City). Bounds: [0, 100]^3."""
    env = Environment(room_bounds=([0.0, 0.0, 0.0], [100.0, 100.0, 100.0]))

    # Downtown Pillars
    env.add_static_obstacle(Box(np.array([25.0, 25.0, 30.0]), np.array([5.0, 5.0, 30.0])))
    env.add_static_obstacle(Box(np.array([75.0, 25.0, 40.0]), np.array([6.0, 6.0, 40.0])))
    env.add_static_obstacle(Box(np.array([25.0, 75.0, 35.0]), np.array([5.0, 5.0, 35.0])))
    env.add_static_obstacle(Box(np.array([75.0, 75.0, 45.0]), np.array([7.0, 7.0, 45.0])))

    # Central Monolith & Skybridge
    env.add_static_obstacle(Box(np.array([50.0, 50.0, 20.0]), np.array([10.0, 10.0, 20.0])))
    env.add_static_obstacle(Box(np.array([50.0, 25.0, 40.0]), np.array([20.0, 4.0, 4.0])))

    # Industrial Cylinders
    env.add_static_obstacle(Cylinder(np.array([10.0, 50.0, 50.0]), 8.0, 50.0))
    env.add_static_obstacle(Cylinder(np.array([90.0, 50.0, 50.0]), 8.0, 50.0))

    # Atmospheric Mines
    env.add_static_obstacle(Sphere(np.array([35.0, 50.0, 70.0]), 12.0))
    env.add_static_obstacle(Sphere(np.array([65.0, 50.0, 75.0]), 10.0))
    env.add_static_obstacle(Sphere(np.array([50.0, 35.0, 80.0]), 14.0))
    env.add_static_obstacle(Sphere(np.array([50.0, 65.0, 65.0]), 11.0))

    # Low-Altitude Domes & Suspended Cup
    env.add_static_obstacle(HalfSphere(
        Sphere(np.array([25.0, 50.0, 0.0]), 15.0),
        Plane(np.array([0.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]))
    ))
    env.add_static_obstacle(HalfSphere(
        Sphere(np.array([75.0, 50.0, 0.0]), 15.0),
        Plane(np.array([0.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]))
    ))
    env.add_static_obstacle(HalfSphere(
        Sphere(np.array([50.0, 50.0, 45.0]), 10.0),
        Plane(np.array([50.0, 50.0, 45.0]), np.array([0.0, 0.0, 1.0]))
    ))

    return env


def build_torture_track() -> Environment:
    """Configuration 2: Sub-Optimality Gap Test (The Torture Track). Bounds: [0, 20]^3."""
    env = Environment(room_bounds=([0.0, 0.0, 0.0], [20.0, 20.0, 20.0]))

    # Corner Trap (Walls A and B form a rigid 'L')
    env.add_static_obstacle(Box(np.array([10.0, 6.0, 10.0]), np.array([2.0, 6.0, 10.0])))
    env.add_static_obstacle(Box(np.array([6.0, 10.0, 10.0]), np.array([6.0, 2.0, 10.0])))

    # The Dome
    env.add_static_obstacle(HalfSphere(
        Sphere(np.array([15.0, 15.0, 5.0]), 4.0),
        Plane(np.array([0.0, 0.0, 5.0]), np.array([0.0, 0.0, 1.0]))
    ))

    return env


def build_stress_phase1(k: int) -> Environment:
    """
    Configurations 3-7: Stress Test Phase 1 (Progressive Saturation). Bounds: [0, 20]^3.

    Progressively adds obstacles at fixed coordinates as k increases
    (k in {0, 2, 4, 6, 8}) to preserve a valid scientific control variable.
    """
    valid_k = {0, 2, 4, 6, 8}
    if k not in valid_k:
        raise ValueError(f"Invalid k: {k}. Must be one of {sorted(valid_k)}.")

    env = Environment(room_bounds=([0.0, 0.0, 0.0], [20.0, 20.0, 20.0]))

    # Configuration 3 (k=0) is empty.
    if k >= 2:
        # Core Blockers
        env.add_static_obstacle(Sphere(np.array([7.0, 13.0, 10.0]), 2.5))
        env.add_static_obstacle(Sphere(np.array([13.0, 7.0, 10.0]), 2.5))
    if k >= 4:
        # Local Minima Traps (inward-facing bowls / saddle points)
        env.add_static_obstacle(HalfSphere(
            Sphere(np.array([5.0, 5.0, 5.0]), 4.0),
            Plane(np.array([5.0, 5.0, 5.0]), np.array([-1.0, -1.0, 1.0]))
        ))
        env.add_static_obstacle(HalfSphere(
            Sphere(np.array([15.0, 15.0, 15.0]), 4.0),
            Plane(np.array([15.0, 15.0, 15.0]), np.array([1.0, 1.0, -1.0]))
        ))
    if k >= 6:
        # Choke Walls (force a narrow central corridor)
        env.add_static_obstacle(Box(np.array([10.0, 4.0, 10.0]), np.array([8.0, 1.0, 10.0])))
        env.add_static_obstacle(Box(np.array([10.0, 16.0, 10.0]), np.array([8.0, 1.0, 10.0])))
    if k >= 8:
        # Vertical Pillars
        env.add_static_obstacle(Cylinder(np.array([3.0, 10.0, 10.0]), 2.0, 10.0))
        env.add_static_obstacle(Cylinder(np.array([17.0, 10.0, 10.0]), 2.0, 10.0))

    return env


def build_csg_maze() -> Environment:
    """Configuration 8: Stress Test Phase 2 (The CSG Maze). Bounds: [0, 20]^3."""
    env = Environment(room_bounds=([0.0, 0.0, 0.0], [20.0, 20.0, 20.0]))

    # Maze Walls (leave X: 0-4 and 16-20 open)
    env.add_static_obstacle(Box(np.array([10.0, 6.0, 10.0]), np.array([6.0, 1.0, 10.0])))
    env.add_static_obstacle(Box(np.array([10.0, 14.0, 10.0]), np.array([6.0, 1.0, 10.0])))

    # Dead End Blocker (seals the left pathway) & Choke Point (right pathway)
    env.add_static_obstacle(Box(np.array([4.0, 10.0, 10.0]), np.array([4.0, 1.0, 10.0])))
    env.add_static_obstacle(Cylinder(np.array([16.0, 10.0, 10.0]), 1.5, 10.0))

    return env


# Convenience registry used by the FastAPI backend for scenario hot-swapping.
def build_scenario(scenario_id: str) -> Environment:
    """Maps a frontend scenario id string to a freshly-built Environment."""
    if scenario_id == "cyber_city":
        return build_cyber_city()
    if scenario_id == "torture_track":
        return build_torture_track()
    if scenario_id == "csg_maze":
        return build_csg_maze()
    if scenario_id.startswith("stress_phase1_k"):
        return build_stress_phase1(int(scenario_id.split("_k")[-1]))
    raise ValueError(f"Unknown scenario id: {scenario_id}")


if __name__ == "__main__":
    print("--- Environment Module Smoke Test ---")
    cc = build_cyber_city()
    print(f"Cyber City   bounds={cc.bounds} obstacles={len(cc.static_obstacles)} (expected 15)")
    tt = build_torture_track()
    print(f"Torture Track bounds={tt.bounds} obstacles={len(tt.static_obstacles)} (expected 3)")
    for k in [0, 2, 4, 6, 8]:
        se = build_stress_phase1(k)
        print(f"Stress P1 k={k} bounds={se.bounds} obstacles={len(se.static_obstacles)} (expected {k})")
    cm = build_csg_maze()
    print(f"CSG Maze     bounds={cm.bounds} obstacles={len(cm.static_obstacles)} (expected 4)")
    print("-------------------------------------")
