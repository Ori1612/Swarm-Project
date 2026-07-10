import numpy as np
from scipy.optimize import minimize
from src.solvers.gradient import approximate_gradient

class SCPSolver:
    def __init__(self, T: int, dt: float = 1.0, drone_radius: float = 0.5):
        self.T = T
        self.dt = dt
        self.drone_radius = drone_radius

    def _objective_function(self, X_flat):
        """
        Quadratic objective: Minimizes the squared velocity (path smoothness/energy).
        """
        X = X_flat.reshape((self.T, 3))
        velocities = np.diff(X, axis=0) / self.dt
        return np.sum(np.linalg.norm(velocities, axis=1)**2)

    def _objective_jacobian(self, X_flat):
        """
        Analytical gradient of the objective to prevent SLSQP numerical linesearch failure.
        """
        X = X_flat.reshape((self.T, 3))
        grad = np.zeros_like(X)
        for t in range(self.T):
            if t > 0:
                grad[t] += 2 * (X[t] - X[t-1]) / (self.dt**2)
            if t < self.T - 1:
                grad[t] -= 2 * (X[t+1] - X[t]) / (self.dt**2)
        return grad.flatten()

    def generate_hyperplane_constraints(self, X_ref, environment, detection_radius=25.0, delta_trust_region=5.0):
        constraints = []
        
        # ---------------------------------------------------------------------
        # 1. Primary Node-Level Constraints
        # ---------------------------------------------------------------------
        for t in range(self.T):
            p_t = X_ref[t]
            nearby_obstacles = environment.get_nearby_obstacles(p_t, t=t, detection_radius=detection_radius)
            
            for obs in nearby_obstacles:
                d = obs.get_distance(p_t, t=t)
                n = approximate_gradient(p_t, obs, t=t)
                
                required_move = self.drone_radius - d
                achievable_move = min(required_move, delta_trust_region * 0.8)
                margin = -achievable_move
                
                constraint = {
                    'type': 'ineq',
                    'fun': lambda X_flat, t_idx=t, m=margin, norm_vec=n, pt=p_t: \
                           norm_vec @ (X_flat[t_idx*3 : (t_idx+1)*3] - pt) + m,
                    'jac': lambda X_flat, t_idx=t, norm_vec=n: \
                           np.concatenate((np.zeros(t_idx * 3), norm_vec, np.zeros(len(X_flat) - (t_idx + 1) * 3)))
                }
                constraints.append(constraint)
                
        # ---------------------------------------------------------------------
        # 2. Inter-Knot Midpoint Constraints (Prevents Tunneling/Aliasing)
        # ---------------------------------------------------------------------
        for t in range(self.T - 1):
            p_t = X_ref[t]
            p_next = X_ref[t+1]
            p_mid = 0.5 * (p_t + p_next)
            
            nearby_obstacles = environment.get_nearby_obstacles(p_mid, t=t, detection_radius=detection_radius)
            
            for obs in nearby_obstacles:
                d = obs.get_distance(p_mid, t=t)
                n = approximate_gradient(p_mid, obs, t=t)
                
                required_move = self.drone_radius - d
                achievable_move = min(required_move, delta_trust_region * 0.8)
                margin = -achievable_move
                
                # First Principles Derivation of the Midpoint Jacobian:
                # p_mid = 0.5 * X_t + 0.5 * X_{t+1}
                # d(p_mid) / d(X_t) = 0.5 * I,  d(p_mid) / d(X_{t+1}) = 0.5 * I
                # Via chain rule, the gradient components are split equally: 0.5 * n
                constraint = {
                    'type': 'ineq',
                    'fun': lambda X_flat, t_idx=t, m=margin, norm_vec=n, pmid=p_mid: \
                           norm_vec @ (0.5 * X_flat[t_idx*3 : (t_idx+1)*3] + 0.5 * X_flat[(t_idx+1)*3 : (t_idx+2)*3] - pmid) + m,
                    'jac': lambda X_flat, t_idx=t, norm_vec=n: \
                           np.concatenate((
                               np.zeros(t_idx * 3), 
                               0.5 * norm_vec, 
                               0.5 * norm_vec, 
                               np.zeros(len(X_flat) - (t_idx + 2) * 3)
                           ))
                }
                constraints.append(constraint)
                
        return constraints

    def solve(self, X_initial, environment, delta_trust_region=5.0, max_scp_iters=20, tol=1e-2):
        X_current = X_initial.copy()
        residuals = []
        
        print("Starting Sequential Convex Programming...")
        
        for m in range(max_scp_iters):
            X_flat_current = X_current.flatten()
            constraints = self.generate_hyperplane_constraints(X_current, environment, delta_trust_region=delta_trust_region)
            
            bounds = []
            eps = 1e-5
            for i, x_val in enumerate(X_flat_current):
                if i < 3 or i >= len(X_flat_current) - 3:
                    bounds.append((x_val - eps, x_val + eps))
                else:
                    bounds.append((x_val - delta_trust_region, x_val + delta_trust_region))
                
            result = minimize(
                fun=self._objective_function,
                jac=self._objective_jacobian,
                x0=X_flat_current,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'disp': False, 'maxiter': 100}
            )
            
            if not result.success:
                print(f"  [!] SLSQP Warning: {result.message}")
                
            X_new = result.x.reshape((self.T, 3))
            step_norm = np.linalg.norm(X_new - X_current)
            residuals.append(step_norm)
            X_current = X_new
            
            print(f"  Iteration {m+1}/{max_scp_iters} | Residual: {step_norm:.6f}")
            
            if step_norm < tol:
                print(f"SCP Converged successfully in {m+1} iterations.")
                break
        else:
            print("SCP reached maximum iterations without falling below tolerance.")
            
        return {
            'trajectory': X_current,
            'residuals': residuals
        }