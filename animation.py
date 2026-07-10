import numpy as np
from guy.renderer import animate_swarm_trajectories
from ori.cbs_solver import CBSSolver
from ori.environment import Environment

def run_rendering_demo(obstacle_instance, trajectories):
    print("\n--- [Part 1] Running rendering and 3D swarm display ---")
    animate_swarm_trajectories(
        trajectories=trajectories,
        obstacle=obstacle_instance,
        bounds=((-10, 10), (-10, 10), (-10, 10)),
        save_path=None
    )

if __name__ == "__main__":
    env_instance = Environment()
    
    class SimpleObstacle:
        def get_distance(self, p, t=0.0): return np.linalg.norm(p) - 3.0
    obs = SimpleObstacle()

    try:
        cbs = CBSSolver(environment=env_instance, radii={0: 0.2, 1: 0.2})
        trajectories = cbs.solve(
            {0: np.array([1.0, 1.0, 1.0]), 1: np.array([9.0, 1.0, 1.0])},
            {0: np.array([9.0, 9.0, 9.0]), 1: np.array([1.0, 9.0, 9.0])}
        )
        if trajectories:
            run_rendering_demo(obs, trajectories)
    except Exception as e:
        print(f" -> Skipping animation: {e}")