import numpy as np

def calculate_cost(X: np.ndarray, environment, x_target: np.ndarray, drone_radius: float) -> float:
    # --- Defensive Shape Verification ---
    assert X.shape[1] == 3, "Trajectory matrix X must have exactly 3 columns (x, y, z)"

    # 1. Kinetic Energy Proxy (Total Path Length)
    diff = X[1:] - X[:-1]
    total_dis = np.sum(np.linalg.norm(diff, axis=1))

    # 2. Goal Penalty (Pulls the final matrix row to the target coordinate)
    goal_penalty = np.linalg.norm(X[-1] - x_target) * 100.0

    # 3. Obstacle Penalty (Evaluated via CSG SDFs)
    X_inner = X[1:-1]
    penalty = 0.0

    # Evaluate the SDF for each intermediate coordinate
    for i in range(X_inner.shape[0]):
        p = X_inner[i]
        
        # i starts at 0, which corresponds to the first inner step (t = 1)
        # Therefore, the current time step for p is i + 1
        d = environment.get_distance(p, t=i+1)

        # If the distance is less than the radius, we have breached the obstacle
        if d < drone_radius:
            # Massive penalty scaling based on the depth of the collision
            penalty += (drone_radius - d) * 1e6

    return total_dis + goal_penalty + penalty