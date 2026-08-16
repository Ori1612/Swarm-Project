import numpy as np
from scipy.optimize import minimize
from src.solvers.gradient import approximate_gradient

from scipy.optimize import minimize, LinearConstraint

class SCPSolver:
    def __init__(self, T: int, dt: float = 1.0, drone_radius: float = 1.0):
        self.T = T
        self.dt = dt
        self.drone_radius = drone_radius

        # Precompute the constant positive-definite Hessian H:
        # J(x) = 1/2 * x^T H x  =>  ∇J(x) = H x
        D1 = np.zeros((self.T - 1, self.T))
        for i in range(self.T - 1):
            D1[i, i] = -1.0
            D1[i, i + 1] = 1.0

        D2 = np.zeros((self.T - 2, self.T))
        for i in range(self.T - 2):
            D2[i, i] = 1.0
            D2[i, i + 1] = -2.0
            D2[i, i + 2] = 1.0

        H1_1d = (2.0 / (self.dt**2)) * (D1.T @ D1)
        H2_1d = (2.0 / (self.dt**4)) * (D2.T @ D2)
        H_1d = (0.9 * H1_1d) + (0.1 * H2_1d)

        # Kronecker product decouples X, Y, and Z axes
        self.H = np.kron(H_1d, np.eye(3))

    def _objective_function(self, X_flat):
        return 0.5 * float(X_flat @ (self.H @ X_flat))

    def _objective_jacobian(self, X_flat):
        return self.H @ X_flat

    def generate_linear_constraints(self, X_ref, environment, detection_radius=None, delta_trust_region=5.0):
        """
        Builds active-set linear hyperplane constraints: A @ x >= b_lower.
        Only constrains obstacles within the immediate interaction buffer (d <= detection_radius)
        and guarantees trust-region feasibility via displacement clamping.
        """
        if detection_radius is None:
            detection_radius = max(6.0, self.drone_radius * 3.0)

        rows_A = []
        lower_bounds = []
        dim = self.T * 3

        # Maximum outward push per SCP step strictly bounded to 70% of trust region
        max_step_push = delta_trust_region * 0.70

        # 1. Primary Node-Level Constraints (t = 1 to T-2)
        for t in range(1, self.T - 1):
            p_t = X_ref[t]
            nearby_obstacles = environment.get_nearby_obstacles(p_t, t=t, detection_radius=detection_radius)

            for obs in nearby_obstacles:
                d = obs.get_distance(p_t, t=t)
                if d > detection_radius:
                    continue

                n = approximate_gradient(p_t, obs, t=t)
                delta_d = self.drone_radius - d

                # First-principles linearization: n @ (x_t - p_t) + d >= r  =>  n @ x_t >= n @ p_t + (r - d)
                # When inside obstacle (delta_d > 0), clamp push to preserve non-empty feasible set
                push = min(delta_d, max_step_push) if delta_d > 0 else delta_d

                row = np.zeros(dim)
                row[t * 3 : (t + 1) * 3] = n
                rows_A.append(row)
                lower_bounds.append(float(n @ p_t + push))

        # 2. Inter-Knot Midpoint Constraints (t = 0 to T-2)
        for t in range(self.T - 1):
            p_t = X_ref[t]
            p_next = X_ref[t + 1]
            p_mid = 0.5 * (p_t + p_next)

            nearby_obstacles = environment.get_nearby_obstacles(p_mid, t=t, detection_radius=detection_radius)

            for obs in nearby_obstacles:
                d = obs.get_distance(p_mid, t=t)
                if d > detection_radius:
                    continue

                n = approximate_gradient(p_mid, obs, t=t)
                delta_d = self.drone_radius - d
                push = min(delta_d, max_step_push) if delta_d > 0 else delta_d

                row = np.zeros(dim)
                row[t * 3 : (t + 1) * 3] = 0.5 * n
                row[(t + 1) * 3 : (t + 2) * 3] = 0.5 * n
                rows_A.append(row)
                lower_bounds.append(float(n @ p_mid + push))

        if len(rows_A) == 0:
            return None

        A = np.vstack(rows_A)
        lb = np.array(lower_bounds)
        ub = np.full_like(lb, np.inf)
        return LinearConstraint(A, lb, ub)

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
            lin_con = self.generate_linear_constraints(X_current, environment, delta_trust_region=current_trust)
            constraints = [lin_con] if lin_con is not None else []

            bounds = []
            for i in range(len(X_flat_current)):
                if i < 3:
                    val = start_pos[i % 3]
                    bounds.append((val, val))
                elif i >= len(X_flat_current) - 3:
                    val = goal_pos[i % 3]
                    bounds.append((val, val))
                else:
                    x_val = X_flat_current[i]
                    bounds.append((x_val - current_trust, x_val + current_trust))

            result = minimize(
                fun=self._objective_function,
                jac=self._objective_jacobian,
                x0=X_flat_current,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'disp': False, 'maxiter': 40, 'ftol': 1e-4}
            )

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