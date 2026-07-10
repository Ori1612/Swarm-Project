import numpy as np
from src.solvers.sa_cost_function import calculate_cost

def run_SA(x_start, x_target, environment, drone_radius, T, epsilon=1e-6, initial_temp=10.0, gamma=0.95):
    """
    Simulated Annealing (SA) Solver utilizing continuous CSG SDFs.
    Returns a T x 3 trajectory matrix.
    """
    # 1. The Initial Guess (Linear interpolation from start to target)
    X = np.linspace(x_start, x_target, T)
    temp = initial_temp
    
    # 2. Calculate the initial cost
    current_cost = calculate_cost(X, environment, x_target, drone_radius)
    
    # 3. The Annealing Loop
    while temp > epsilon:
        X_new = np.copy(X)
        
        # Generate random, normal noise for the intermediate steps
        noise = np.random.normal(0, temp, (T - 2, 3))
        X_new[1:-1, :] += noise

        # Calculate the new trajectory's cost function using CSG
        new_cost = calculate_cost(X_new, environment, x_target, drone_radius)
        delta_E = new_cost - current_cost

        # 1st Condition: Improvement accepted unconditionally
        if delta_E < 0:
            X = X_new
            current_cost = new_cost
        else:
            # 2nd Condition: Worse trajectory accepted probabilistically (Boltzmann)
            p_acc = np.exp(-delta_E / temp)
            p = np.random.uniform(0, 1)  

            if p_acc >= p:
                X = X_new
                current_cost = new_cost

        temp *= gamma

    return X