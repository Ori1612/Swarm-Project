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

                # Generate three unique initial guesses to avoid local minima
                candidates = []
                # 1. Straight Line
                candidates.append(np.linspace(start_pos, goal_pos, self.T))
                # 2. Geometric Arc (Existing heuristic)
                arc = np.sin(np.linspace(0, np.pi, self.T))[:, np.newaxis]
                candidates.append(np.linspace(start_pos, goal_pos, self.T) + arc * np.array([5.0, 5.0, 4.0]))
                
                best_traj = None
                best_cost = float('inf')

                print(f"  [SCP] Evaluating {len(candidates)} multi-start initializations...")
                for X_init in candidates:
                    # Reduced max_scp_iters from default 50 to 25 for speed
                    result = scp.solve(X_init, self.environment, delta_trust_region=dynamic_trust, max_scp_iters=25)
                    # Cost is evaluated via the acceleration-penalty objective
                    cost = scp._objective_function(result['trajectory'].flatten())
                    
                    if cost < best_cost:
                        best_cost = cost
                        best_traj = result['trajectory']
                
                X_i = best_traj
            else:
                raise ValueError("Unknown solver type! Choose 'APF', 'SA', or 'SCP'.")

            # 2. Fulfill Data Contract: Save the full T x 3 matrix for the visualization module
            all_trajectories.append(X_i)

            # 3. Constant Velocity/Padding: Ensure the drone acts as an obstacle 
            # for the entire visualization window (T steps), even when hovering at the goal.
            # We explicitly fill any unused time steps with the final goal position.
            
            # The solver output X_i is already size T. 
            # We ensure the drone stays at the goal for the remainder of T.
            # Relax the clamp radius to 1.5x the drone radius for better persistence
            for t in range(len(X_i)):
                if np.linalg.norm(X_i[t] - goal_pos) < radius * 1.5:
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

    def query_kkt_hyperplanes(self, point_list: list, t: int = 0) -> list:
        """
        On-Demand API Endpoint for Guy's UI.
        Accepts a 3D coordinate from the frontend, queries the CSG environment, 
        and returns all active hyperplanes within the Trust Region.
        """
        p_t = np.array(point_list, dtype=float)
        # Match the SCP solver detection radius (25.0) to ensure consistency
        nearby_obstacles = self.environment.get_nearby_obstacles(p_t, t=t, detection_radius=25.0)
        
        hyperplanes = []
        for obs in nearby_obstacles:
            d = obs.get_distance(p_t, t=t)
            n = approximate_gradient(p_t, obs, t=t)
            
            hyperplanes.append({
                'distance_scalar': float(d),
                'normal_vector': n.tolist()
            })
            
        return hyperplanes