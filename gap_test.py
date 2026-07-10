"""
gap_test.py  --  Sub-Optimality Gap Test (The Torture Track)

Completely rewritten per the Gap Test Guide (Directive 1):
  * Iterates the grid-resolution sequence dx in {2.0, 1.0, 0.5, 0.2}.
  * Runs the discrete CBS solver and the continuous SCP solver.
  * Records CBS path length + the true low-level A* node expansions
    (the "memory wall"), and the SCP path length (a flat geodesic line).
  * Pipes everything to the headless benchmarking module for PNG export.

Run:  python gap_test.py
"""

import numpy as np

from ori.cbs_solver import CBSSolver
from ori.manager import SwarmManager
from guy.environments import build_torture_track
from guy.benchmarks import OptimizationDiagnostics

# dx sequence. Do NOT go finer than 0.2 (the guide warns of OS memory kills).
DELTA_X_VALUES = [2.0, 1.0, 0.5, 0.2]

# Safeguard: abort a single A* search that expands more nodes than this, so a
# fine grid degrades gracefully instead of exhausting RAM. Generous enough to
# still expose the cubic explosion trend.
MAX_ASTAR_NODES = 200_000

# SCP horizon. SCP (SLSQP) cost grows steeply with T; 30 steps is smooth
# enough for a geodesic while keeping the solve to a few seconds.
SCP_T = 30


def run_gap_test():
    print("Initializing Sub-Optimality Gap Test (Torture Track)...")
    env = build_torture_track()

    # Using the mathematically proven boundary coordinates to force a 3D climb
    # over the Dome while skimming the Corner Trap apex with exactly 0 clearance.
    start_pos = np.array([16.0, 2.0, 5.0])
    goal_pos = np.array([2.0, 16.0, 5.0])
    drone_radius = 0.5

    # ---- SCP: continuous reference. Independent of dx, so compute it ONCE. ----
    print("\n--- Running SCP (continuous geodesic, resolution-independent) ---")
    manager = SwarmManager(T=SCP_T, environment=env)
    scp_paths = manager.solve_swarm(
        [{'start': start_pos, 'goal': goal_pos, 'radius': drone_radius}],
        solver_type='SCP'
    )
    scp_len = OptimizationDiagnostics.calculate_path_length(scp_paths[0])
    print(f" -> SCP path length: {scp_len:.2f} m")

    cbs_lengths = []
    scp_lengths = []
    nodes_expanded_list = []

    for dx in DELTA_X_VALUES:
        print(f"\n--- Running CBS at grid resolution dx = {dx} ---")

        # Fresh env per resolution keeps each discretization independent and clean.
        cbs_env = build_torture_track()
        cbs_solver = CBSSolver(cbs_env, radii={0: drone_radius},
                               grid_resolution=dx, max_nodes=MAX_ASTAR_NODES)
        cbs_paths = cbs_solver.solve(start_positions={0: start_pos},
                                     goal_positions={0: goal_pos})

        # True memory-wall metric: total low-level A* nodes expanded (NOT the
        # high-level CBS count, which is always 1 for a single drone).
        nodes_expanded = cbs_solver.astar_nodes_expanded

        if cbs_paths is None or len(cbs_paths) == 0:
            print(f"  [!] CBS returned no path at dx={dx} "
                  f"(hit node cap {MAX_ASTAR_NODES} or infeasible grid).")
            cbs_len = np.nan
        else:
            cbs_len = OptimizationDiagnostics.calculate_path_length(cbs_paths[0])

        cbs_lengths.append(cbs_len)
        scp_lengths.append(scp_len)
        nodes_expanded_list.append(nodes_expanded)

        print(f"> Result @ dx={dx}: CBS Length={cbs_len:.2f} m, "
              f"SCP Length={scp_len:.2f} m, A* Nodes={nodes_expanded}")

    print("\n--- Gap Test complete. Rendering headless graphs... ---")
    OptimizationDiagnostics.plot_resolution_vs_path_length(
        DELTA_X_VALUES, cbs_lengths, scp_lengths,
        "gap_test_resolution_vs_pathlength.png"
    )
    OptimizationDiagnostics.plot_resolution_vs_nodes_expanded(
        DELTA_X_VALUES, nodes_expanded_list,
        "gap_test_resolution_vs_nodes_expanded.png"
    )
    print("Graphs written:")
    print("  - gap_test_resolution_vs_pathlength.png")
    print("  - gap_test_resolution_vs_nodes_expanded.png")

    # Report the headline sub-optimality gap at the finest feasible resolution.
    finite = [(dx, c) for dx, c in zip(DELTA_X_VALUES, cbs_lengths) if not np.isnan(c)]
    if finite:
        dx_best, cbs_best = finite[-1]
        gap = ((cbs_best - scp_len) / scp_len) * 100.0
        print(f"\nSub-optimality gap at dx={dx_best}: CBS is {gap:.1f}% longer than the SCP geodesic.")


if __name__ == "__main__":
    run_gap_test()