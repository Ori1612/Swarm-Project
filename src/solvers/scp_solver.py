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
        Analytical gradient of the full objective function (90% Velocity + 10% Acceleration).
        Uses exact vectorized partial derivatives to evaluate all boundaries correctly.
        """
        X = X_flat.reshape((self.T, 3))
        
        # 1. Velocity Gradient (Distance Cost)
        grad_vel = np.zeros_like(X)
        vel = np.diff(X, axis=0) 
        grad_vel[:-1] -= 2 * vel / (self.dt**2)
        grad_vel[1:] += 2 * vel / (self.dt**2)
        
        # 2. Acceleration Gradient (Smoothness Cost)
        grad_accel = np.zeros_like(X)
        accel = (X[2:] - 2*X[1:-1] + X[:-2])
        grad_accel[:-2] += 2 * accel / (self.dt**4)
        grad_accel[1:-1] -= 4 * accel / (self.dt**4)
        grad_accel[2:] += 2 * accel / (self.dt**4)
        
        # Combine using the exact weights from the objective function
        grad = (0.9 * grad_vel) + (0.1 * grad_accel)
        return grad.flatten()

    def generate_hyperplane_constraints(self, X_ref, environment, detection_radius=25.0, delta_trust_region=5.0):
        constraints = []
        
        # ---------------------------------------------------------------------
        # 1. Primary Node-Level Constraints
        # ---------------------------------------------------------------------
        # Skip t=0 (Start) and t=T-1 (Goal) to ensure the optimizer does not 
        # nudge the endpoints to satisfy collision constraints.
        for t in range(1, self.T - 1):
            p_t = X_ref[t]
            nearby_obstacles = environment.get_nearby_obstacles(p_t, t=t, detection_radius=detection_radius)
            
            for obs in nearby_obstacles:
                d = obs.get_distance(p_t, t=t)
                n = approximate_gradient(p_t, obs, t=t)
                
                # Tighten buffer to match CBS grid-center tolerance (allow closer skimming)
                required_move = (self.drone_radius * 1) - d
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

    def solve(self, X_initial, environment, delta_trust_region=5.0, max_scp_iters=25, tol=1e-3):
        X_current = X_initial.copy()
        start_pos = X_initial[0].copy()
        goal_pos = X_initial[-1].copy()
        residuals = []
        
        print("Starting Sequential Convex Programming...")
        
        # Ensure trust region is a variable we can modify during convergence attempts
        current_trust = delta_trust_region
        for m in range(max_scp_iters):
            X_flat_current = X_current.flatten()
            constraints = self.generate_hyperplane_constraints(X_current, environment, delta_trust_region=current_trust)
            
            bounds = []
            eps = 1e-9 # Tightened tolerance for pinning
            for i in range(len(X_flat_current)):
                # Pin start (i=0,1,2) and goal (last 3 indices) to absolute values
                if i < 3:
                    val = start_pos[i % 3]
                    bounds.append((val, val))
                elif i >= len(X_flat_current) - 3:
                    val = goal_pos[i % 3]
                    bounds.append((val, val))
                else:
                    # Floating nodes are bounded by the trust region
                    x_val = X_flat_current[i]
                    bounds.append((x_val - current_trust, x_val + current_trust))
                
            result = minimize(
                fun=self._objective_function,
                jac=self._objective_jacobian,
                x0=X_flat_current,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'disp': False, 'maxiter': 200, 'ftol': 1e-4}
            )
            
            if not result.success:
                print(f"  [!] SLSQP Warning: {result.message}")
                # If solver struggles, shrink the trust region to recover feasibility
                delta_trust_region *= 0.5
                current_trust = delta_trust_region
                print(f"  [!] Shrinking trust region to {current_trust:.2f} for stability.")
                
            X_new = result.x.reshape((self.T, 3))
            # HARD PIN: Force the endpoints back to the original values
            X_new[0] = start_pos
            X_new[-1] = goal_pos
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