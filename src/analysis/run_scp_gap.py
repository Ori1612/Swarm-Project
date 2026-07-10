"""
run_optimal_gap.py
Autonomous test harness to run the continuous SCP geodesic solver 
on the Torture Track using the mathematically optimal boundary conditions.
"""

import numpy as np
from src.engine.scenario_configs import build_torture_track
from src.solvers.manager import SwarmManager

def main():
    # 1. Instantiate the scientifically controlled environment configuration
    env = build_torture_track()
    
    # 2. Assign the optimal 3D coordinate pairs (forcing a non-planar geodesic climb)
    start_pos = np.array([16.0, 2.0, 5.0])
    goal_pos = np.array([2.0, 16.0, 5.0])
    drone_radius = 0.5
    
    # 3. Use the exact temporal horizon specified by the benchmark guidelines
    SCP_T = 30
    
    print("================================================================")
    # Clear visualization details of parameters
    print(f"Executing Optimal Gap Test Solver")
    print(f"Start Coordinate: {start_pos}")
    print(f"Goal Coordinate:  {goal_pos}")
    print(f"Horizon Steps T:  {SCP_T}")
    print("=====================================================\n")

    # 4. Initialize the SwarmManager instance
    manager = SwarmManager(T=SCP_T, environment=env)
    
    # 5. Invoke the continuous solver under the standard data contract
    print("Triggering SCP Optimization Loop...")
    trajectories = manager.solve_swarm(
        [{'start': start_pos, 'goal': goal_pos, 'radius': drone_radius}],
        solver_type='SCP'
    )
    
    # 6. Extract and format the complete T x 3 trajectory matrix
    trajectory_matrix = trajectories[0]
    
    print("\n================================================================")
    print("                   OPTIMIZED TRAJECTORY MATRIX                  ")
    print("================================================================")
    print("  Step  |      X       |      Y       |      Z       ")
    print("------------------------------------------------------------")
    for t_idx, position in enumerate(trajectory_matrix):
        print(f"   {t_idx:02d}   |   {position[0]:8.4f}   |   {position[1]:8.4f}   |   {position[2]:8.4f}   ")
    print("================================================================")

if __name__ == "__main__":
    main()