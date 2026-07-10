import numpy as np
from ori.gradient import approximate_gradient

def run_APF(x_start, x_target, environment, drone_radius, T, alpha=0.1, k_att=1.0, k_rep=10.0, rho_0=2.0):
    """
    Artificial Potential Fields (APF) Solver.
    Simulates a 1st-order gradient descent physics engine.
    Returns a T x 3 trajectory matrix.
    """
    X = np.zeros((T, 3))
    X[0] = x_start
    curr_pos = np.copy(x_start)
    
    for t in range(1, T):
        # 1. Attractive Force (pulls toward the target)
        F_att = -k_att * (curr_pos - x_target)
        
        # 2. Repulsive Force (pushes away from obstacles)
        d = environment.get_distance(curr_pos, t=t)
        F_rep = np.zeros(3)
        
        # Only activate repulsion if within the influence radius
        if d < rho_0:
            # Calculate the finite-difference normal vector
            n = approximate_gradient(curr_pos, environment, t=t)            
            # Bound the distance to prevent division by zero during a collision
            safe_d = max(d - drone_radius, 0.01) 
            
            # APF magnitude calculation
            magnitude = k_rep * (1.0 / safe_d - 1.0 / rho_0) * (1.0 / (safe_d**2))
            F_rep = magnitude * n 
            
        # Execute the gradient descent step
        curr_pos = curr_pos + alpha * (F_att + F_rep)
        X[t] = np.copy(curr_pos)
        
    return X