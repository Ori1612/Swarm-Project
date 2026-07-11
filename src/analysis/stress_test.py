"""
stress_test.py  --  Dual-Axis Stress Test Architecture

Rewritten per the Stress Test Guide (Section 5):
  * Phase 1 (run_phase1_obstacle_scaling): fixed N=4 drones, progressive
    saturation k in {0,2,4,6,8}; measures APF/SA/SCP collision-failure rate.
  * Phase 2 (run_phase2_swarm_scaling): static CSG maze, swarm scale
    N in {2,4,6,8,10}; measures SA vs SCP runtime (APF excluded).

Both phases render headless PNG charts via the benchmarking module.

Run:  python stress_test.py
"""

import time
import numpy as np

from src.solvers.manager import SwarmManager
from src.engine.scenario_configs import build_stress_phase1, build_csg_maze
from src.engine.benchmarks import OptimizationDiagnostics
from src.engine.swarm_adapter import SwarmBenchmarkAdapter

T_HORIZON = 30  # SCP (SLSQP) cost grows steeply with T; 30 keeps the suite tractable
DRONE_RADIUS = 0.5


def run_phase1_obstacle_scaling(trials=3):
    """Phase 1: Failure Rate vs. Environmental Complexity (non-convexity)."""
    print("\n=== Phase 1: Obstacle Scaling (Non-Convexity) ===")
    k_values = [0, 2, 4, 6, 8]
    solvers = ['APF', 'SA', 'SCP']
    n_drones = 4

    # Fixed start/goal pairs that drive all 4 drones through the room centre.
    # Phase 1: Fixed cross-pattern coordinates for scientific control [cite: 111, 113]
    fixed_drones = [
        {'id': 'D1', 'start': np.array([2.0, 8.0, 10.0]),  'goal': np.array([18.0, 8.0, 10.0]),  'radius': DRONE_RADIUS},
        {'id': 'D2', 'start': np.array([2.0, 12.0, 10.0]), 'goal': np.array([18.0, 12.0, 10.0]), 'radius': DRONE_RADIUS},
        {'id': 'D3', 'start': np.array([2.0, 10.0, 8.0]),  'goal': np.array([18.0, 10.0, 8.0]),  'radius': DRONE_RADIUS},
        {'id': 'D4', 'start': np.array([2.0, 10.0, 12.0]), 'goal': np.array([18.0, 10.0, 12.0]), 'radius': DRONE_RADIUS},
    ]

    def phase1_factory(k, solver_type):
        def run_trial():
            # MOVED INSIDE: Fresh environment for every single trial!
            env = build_stress_phase1(k)  
            manager = SwarmManager(T=T_HORIZON, environment=env)
            start_time = time.time()
            trajectories = manager.solve_swarm(fixed_drones, solver_type=solver_type)
            elapsed = time.time() - start_time

            radii_dict = {i: DRONE_RADIUS for i in range(n_drones)}
            has_collision = SwarmBenchmarkAdapter.check_swarm_collisions(trajectories, radii_dict)

            reached_goals = all(
                np.linalg.norm(traj[-1] - fixed_drones[i]['goal']) <= 1.0
                for i, traj in enumerate(trajectories)
            )
            success = (not has_collision) and reached_goals
            return success, elapsed

        return run_trial

    save_path = "stress_phase1_failure_rate.png"
    OptimizationDiagnostics.run_obstacle_scaling_benchmark(
        callback_factory=phase1_factory,
        k_values=k_values,
        algorithms=solvers,
        trials=trials,
        save_path=save_path,
    )
    print(f"Phase 1 complete. Chart saved to: {save_path}")


def run_phase2_swarm_scaling(trials=1):
    """Phase 2: Runtime vs. Swarm Scale (complexity) on the static CSG maze."""
    print("\n=== Phase 2: Swarm Scaling (Complexity Limit) ===")
    n_values = [2, 4, 6, 8, 10]
    solvers = ['SA', 'SCP']              # APF excluded (Phase 1 proves it fails the maze)

    def phase2_factory(n, solver_type):
        drones = []
        for i in range(n):
            # Fan-out: Linear Y-axis distribution to force funneling at X=16 [cite: 93, 124]
            y_offset = (i - (n - 1) / 2.0) * 1.5 
            start = np.array([2.0, 10.0 + y_offset, 10.0])
            goal = np.array([18.0, 10.0 + y_offset, 10.0])
            drones.append({'id': f'S{i}', 'start': start, 'goal': goal, 'radius': DRONE_RADIUS})

        def run_trial():
            # MOVED INSIDE: Fresh environment for every single trial!
            env = build_csg_maze()
            manager = SwarmManager(T=T_HORIZON, environment=env)
            start_time = time.time()
            _ = manager.solve_swarm(drones, solver_type=solver_type)
            return True, time.time() - start_time  # only runtime matters here

        return run_trial

    save_path = "stress_phase2_runtime.png"
    OptimizationDiagnostics.run_swarm_scaling_benchmark(
        swarm_sizes=n_values,
        algorithms=solvers,
        callback_factory=phase2_factory,
        save_path=save_path,
        trials=trials,
    )
    print(f"Phase 2 complete. Chart saved to: {save_path}")


if __name__ == "__main__":
    run_phase1_obstacle_scaling()
    run_phase2_swarm_scaling()
