"""
run_cbs_gap.py
Autonomous test harness to run the discrete CBS solver 
on the Torture Track to verify voxel circumradius padding and A* routing.
"""

import numpy as np
from src.engine.scenario_configs import build_torture_track
from src.solvers.cbs_solver import CBSSolver

def main():
    # 1. Instantiate the scientifically controlled environment
    env = build_torture_track()
    
    # 2. Assign the exact mathematically proven boundary conditions
    start_pos = np.array([16.0, 2.0, 5.0])
    goal_pos = np.array([2.0, 16.0, 5.0])
    drone_radius = 0.5
    
    # 3. Define the Grid Resolution for the test
    dx = 0.5
    
    print("================================================================")
    print(f"Executing Discrete CBS Gap Test Solver")
    print(f"Start Coordinate: {start_pos}")
    print(f"Goal Coordinate:  {goal_pos}")
    print(f"Grid Resolution (dx): {dx} m")
    print("=====================================================\n")

    # 4. Initialize the CBS Solver (which triggers the SDF voxelization)
    cbs_solver = CBSSolver(
        environment=env, 
        radii={0: drone_radius}, 
        grid_resolution=dx, 
        max_nodes=200000
    )
    
    # 5. Invoke the discrete A* search
    print("\nTriggering CBS Optimization Loop...")
    trajectories = cbs_solver.solve(
        start_positions={0: start_pos}, 
        goal_positions={0: goal_pos}
    )
    
    if trajectories is None or len(trajectories) == 0:
        print("\n[!] FATAL: CBS failed to find a valid discrete path.")
        return

    # 6. Extract the path for the primary drone
    trajectory_matrix = trajectories[0]
    
    print(f"\nCBS Converged successfully. Expanded {cbs_solver.astar_nodes_expanded} A* nodes.")
    print("================================================================")
    print("                   DISCRETE TRAJECTORY MATRIX                   ")
    print("================================================================")
    print("  Step  |      X       |      Y       |      Z       ")
    print("------------------------------------------------------------")
    for t_idx, position in enumerate(trajectory_matrix):
        print(f"   {t_idx:02d}   |   {position[0]:8.4f}   |   {position[1]:8.4f}   |   {position[2]:8.4f}   ")
    print("================================================================")

if __name__ == "__main__":
    main()