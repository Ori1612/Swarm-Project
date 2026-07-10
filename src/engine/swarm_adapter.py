import time
import numpy as np

class SwarmBenchmarkAdapter:
    """
    Glue layer connecting Guy's benchmarking suite to Ori's SwarmManager interface.
    Generates test configurations, verifies collision-free safety constraints, and formats outputs.
    """
    @staticmethod
    def check_swarm_collisions(trajectories, drone_radii):
        """
        Evaluates inter-drone safety constraints across all time steps t:
        ||x_{i,t} - x_{j,t}||_2 >= r_i + r_j
        Returns True if a collision is detected, False if completely safe.
        """
        num_drones = len(trajectories)
        if num_drones < 2:
            return False
            
        time_steps = trajectories[0].shape[0]
        for t in range(time_steps):
            for i in range(num_drones):
                for j in range(i + 1, num_drones):
                    dist = np.linalg.norm(trajectories[i][t] - trajectories[j][t])
                    min_safe_dist = drone_radii[i] + drone_radii[j]
                    if dist < min_safe_dist:
                        return True
        return False

    @classmethod
    def create_solver_callback(cls, swarm_manager_instance, solver_type, bounds=((-8, 8), (-8, 8), (-8, 8))):
        """
        Creates a standardized callback matching run_stress_test expectation:
        solver_fn(num_drones=n) -> (success_bool, runtime_float)
        """
        def solver_fn(num_drones):
            drones_list = []
            drone_radii = []
            for d_id in range(num_drones):
                radius = 0.5
                start = np.random.uniform([b[0] for b in bounds], [b[1] for b in bounds])
                goal = np.random.uniform([b[0] for b in bounds], [b[1] for b in bounds])
                
                drones_list.append({
                    'id': d_id,
                    'start': start,
                    'goal': goal,
                    'radius': radius
                })
                drone_radii.append(radius)

            start_time = time.time()
            try:
                trajectories = swarm_manager_instance.solve_swarm(drones_list, solver_type=solver_type)
                elapsed_time = time.time() - start_time
                
                has_collision = cls.check_swarm_collisions(trajectories, drone_radii)
                # Verify paths are non-empty, not None, and contain valid numbers (no NaNs/Infs)
                is_valid = all(
                    traj is not None and 
                    len(traj) > 0 and 
                    not np.isnan(traj).any() and 
                    not np.isinf(traj).any() 
                    for traj in trajectories
                )
                success = not has_collision and is_valid
                return success, elapsed_time
            except Exception:
                return False, time.time() - start_time

        return solver_fn
