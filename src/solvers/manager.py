import numpy as np
import json
from src.physics.environment import Environment
from src.physics.obstacles.dynamic_drone import DynamicDroneObstacle

from src.solvers.apf_solver import run_APF
from src.solvers.sa_solver import run_SA
from src.solvers.scp_solver import SCPSolver
from src.solvers.gradient import approximate_gradient

class SwarmManager:
    def __init__(self, T: int, environment: Environment):
        self.T = T
        self.environment = environment

    def solve_swarm(self, drones: list, solver_type: str = 'APF') -> list:
        """
        Executes Decoupled Prioritized Planning for a swarm of drones.
        
        Parameters:
        drones: list of dictionaries, e.g., [{'start': p1, 'goal': g1, 'radius': r1}, ...]
        solver_type: 'APF', 'SA', or 'SCP'
        
        Returns:
        list of T x 3 numpy arrays (strict compliance with the visualization Data Contract).
        """
        
        all_trajectories = []

        for i, drone in enumerate(drones):
            start_pos = np.array(drone['start'], dtype=float)
            goal_pos = np.array(drone['goal'], dtype=float)
            radius = drone['radius']

            # 1. Execute the requested Continuous Solver
            if solver_type == 'APF':
                X_i = run_APF(start_pos, goal_pos, self.environment, radius, self.T)
                
            elif solver_type == 'SA':
                X_i = run_SA(start_pos, goal_pos, self.environment, radius, self.T)
                
            elif solver_type == 'SCP':
                scp = SCPSolver(self.T, dt=1.0, drone_radius=radius)
                env_span = np.array(self.environment.bounds[1]) - np.array(self.environment.bounds[0])
                dynamic_trust = max(2.0, np.max(env_span) * 0.05)

                # Generate distinct high-clearance multi-start initializations
                straight = np.linspace(start_pos, goal_pos, self.T)
                arc = np.sin(np.linspace(0, np.pi, self.T))[:, np.newaxis]
                
                # Perpendicular lateral horizontal vector in XY plane
                disp_xy = goal_pos[:2] - start_pos[:2]
                norm_xy = np.linalg.norm(disp_xy)
                perp_xy = np.array([-disp_xy[1], disp_xy[0], 0.0]) / norm_xy if norm_xy > 1e-4 else np.array([1.0, 0.0, 0.0])

                candidates = [
                    # 1. Straight Line Geodesic
                    straight,
                    # 2. High-Altitude Vault Arc (Clears towering downtown monoliths)
                    straight + arc * np.array([0.0, 0.0, env_span[2] * 0.50]),
                    # 3. Lateral Left Evasive Arc
                    straight + arc * (perp_xy * (env_span[0] * 0.30) + np.array([0.0, 0.0, env_span[2] * 0.15])),
                    # 4. Lateral Right Evasive Arc
                    straight + arc * (-perp_xy * (env_span[0] * 0.30) + np.array([0.0, 0.0, env_span[2] * 0.15]))
                ]

                best_traj = None
                best_cost = float('inf')

                from concurrent.futures import ThreadPoolExecutor

                print(f"  [SCP] Evaluating {len(candidates)} multi-start initializations in parallel...")

                def _eval_candidate(X_init):
                    res = scp.solve(X_init, self.environment, delta_trust_region=dynamic_trust, max_scp_iters=10)
                    traj = res['trajectory']
                    base_cost = scp._objective_function(traj.flatten())

                    # Collision penetration penalty
                    collision_penalty = 0.0
                    for pt in traj:
                        d = self.environment.get_distance(pt)
                        if d < radius:
                            collision_penalty += (radius - d) * 100000.0

                    return base_cost + collision_penalty, traj

                with ThreadPoolExecutor(max_workers=len(candidates)) as executor:
                    candidate_results = list(executor.map(_eval_candidate, candidates))

                best_cost, best_traj = min(candidate_results, key=lambda item: item[0])
                X_i = best_traj
            else:
                raise ValueError("Unknown solver type! Choose 'APF', 'SA', or 'SCP'.")

            # 2. Fulfill Data Contract: Save the full T x 3 matrix for the visualization module
            all_trajectories.append(X_i)

            # 3. Constant Velocity/Padding: Ensure the drone acts as an obstacle 
            # for the entire visualization window (T steps), even when hovering at the goal.
            # We explicitly fill any unused time steps with the final goal position.
            
            # The solver output X_i is already size T. 
            # We ensure the drone stays at the goal for the remainder of T once arrived.
            for t in range(len(X_i)):
                if np.linalg.norm(X_i[t] - goal_pos) < min(0.35, radius * 0.5):
                    X_i[t:] = goal_pos
                    break

            # 4. Update the Swarm Environment
            # Pass the FULL trajectory so it remains a physical obstacle for all T steps.
            dynamic_obs = DynamicDroneObstacle(X_i, radius)
            self.environment.add_dynamic_obstacle(dynamic_obs)

        return all_trajectories

    # =======================================================
    # API Bridge Functions for the Interactive 3D Web UI
    # =======================================================

    def export_swarm_to_json(self, trajectories: list, filepath: str = "swarm_data.json") -> list:
        """
        Converts the finalized T x 3 NumPy arrays into standard nested lists 
        so the Three.js frontend can read the spatial data.
        """
        json_data = [traj.tolist() for traj in trajectories]
        with open(filepath, 'w') as f:
            json.dump(json_data, f)
        return json_data