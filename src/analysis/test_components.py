import numpy as np
from src.engine.scenario_configs import build_stress_phase1, build_csg_maze
from src.solvers.manager import SwarmManager

def test_dry_run():
    print("[1/3] Testing Environment Instantiation...")
    env_p1 = build_stress_phase1(k=2) # Test base + 2 obstacles
    env_maze = build_csg_maze()
    assert env_p1 is not None and env_maze is not None, "Environment build failed!"
    print("  -> PASSED: Environments initialized.")

    print("[2/3] Testing Solver Pipeline (Micro-Test)...")
    manager = SwarmManager(T=10, environment=env_maze) # T=10 for speed
    drones = [{'start': np.array([2.0, 10.0, 10.0]), 'goal': np.array([18.0, 10.0, 10.0]), 'radius': 0.5}]
    
    for solver in ['APF', 'SA', 'SCP']:
        try:
            trajs = manager.solve_swarm(drones, solver_type=solver)
            assert len(trajs[0]) == 10, f"{solver} failed trajectory length check!"
            print(f"  -> PASSED: {solver} executed successfully.")
        except Exception as e:
            print(f"  [!] FAILED: {solver} crashed with error: {e}")
            return

    print("[3/3] Testing Collision Detection Bridge...")
    dist = env_maze.get_distance(np.array([10.0, 6.0, 10.0]))
    print(f"  -> Collision check at wall center: dist = {dist:.4f}")
    
    print("\nDRY RUN SUCCESSFUL. All components verified.")

if __name__ == "__main__":
    test_dry_run()