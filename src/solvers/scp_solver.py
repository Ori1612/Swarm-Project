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
        Weighted objective: Minimizes distance (velocity) AND smoothness (acceleration).
        Weighting: 90% Distance, 10% Smoothness.
        """
        X = X_flat.reshape((self.T, 3))
        # Velocity term (Distance penalty)
        vel = np.diff(X, axis=0) / self.dt
        length_cost = np.sum(np.linalg.norm(vel, axis=1)**2)
        
        # Acceleration term (Smoothness penalty)
        accel = (X[2:] - 2*X[1:-1] + X[:-2]) / (self.dt**2)
        smooth_cost = np.sum(np.linalg.norm(accel, axis=1)**2)
        
        # Balance: Primary goal is distance. Secondary is smoothness.
        return (0.9 * length_cost) + (0.1 * smooth_cost)

    def _objective_jacobian(self, X_flat):
        """
        Analytical gradient of the squared acceleration objective using the 1-4-6-4-1 stencil.
        """
        X = X_flat.reshape((self.T, 3))
        grad = np.zeros_like(X)
        # We define a helper for the acceleration vector
        # acc[t] = x_{t+1} - 2*x_t + x_{t-1}
        # The gradient is derived from the expansion of the squared norm.
        
        # This stencil applies to indices 2 through T-3. 
        # Boundaries are handled implicitly by the loop structure.
        for t in range(2, self.T - 2):
            # The stencil: x_{t-2} - 4x_{t-1} + 6x_t - 4x_{t+1} + x_{t+2}
            grad[t] = 2 * (X[t-2] - 4*X[t-1] + 6*X[t] - 4*X[t+1] + X[t+2]) / (self.dt**4)
            
        # We ignore boundary conditions for the acceleration cost (or set them to 0) 
        # to ensure the endpoints are free to satisfy the start/goal constraints.
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
                
                # Tighten buffer to match CBS grid-center tolerance (allow closer skimming)
                required_move = (self.drone_radius * 0.9) - d
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

    def solve(self, X_initial, environment, delta_trust_region=5.0, max_scp_iters=50, tol=1e-4):
        X_current = X_initial.copy()
        residuals = []
        
        print("Starting Sequential Convex Programming...")
        
        # Ensure trust region is a variable we can modify during convergence attempts
        current_trust = delta_trust_region
        for m in range(max_scp_iters):
            X_flat_current = X_current.flatten()
            constraints = self.generate_hyperplane_constraints(X_current, environment, delta_trust_region=current_trust)
            
            bounds = []
            eps = 1e-5
            for i, x_val in enumerate(X_flat_current):
                if i < 3 or i >= len(X_flat_current) - 3:
                    bounds.append((x_val - eps, x_val + eps))
                else:
                    bounds.append((x_val - current_trust, x_val + current_trust))
                
            result = minimize(
                fun=self._objective_function,
                jac=self._objective_jacobian,
                x0=X_flat_current,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'disp': False, 'maxiter': 500, 'ftol': 1e-6}
            )
            
            if not result.success:
                print(f"  [!] SLSQP Warning: {result.message}")
                # If solver struggles, shrink the trust region to recover feasibility
                delta_trust_region *= 0.5
                current_trust = delta_trust_region
                print(f"  [!] Shrinking trust region to {current_trust:.2f} for stability.")
                
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