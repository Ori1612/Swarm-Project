import numpy as np
from src.physics.obstacles.base import Obstacle

def approximate_gradient(point: np.ndarray, obstacle: Obstacle, t: float = 0.0, h: float = 1e-5) -> np.ndarray:
    
    """
    Approximates the normalized spatial gradient ∇SDF for a specific obstacle using Central Finite Differences.
    Includes a symmetry-breaking safeguard for singularities/saddle points.
    """
    grad = np.zeros(3)
    I = np.eye(3)  
    
    for i in range(3):
        p_plus = point + h * I[i]
        p_minus = point - h * I[i]
        
        # Polymorphic call: Native array and time step
        d_plus = obstacle.get_distance(p_plus, t=t)
        d_minus = obstacle.get_distance(p_minus, t=t)
        
        grad[i] = (d_plus - d_minus) / (2 * h)
        
    # Normalize to a unit vector for stable KKT hyperplanes
    norm = np.linalg.norm(grad)
    
    if norm > 1e-8:
        return grad / norm
        
    # ==============================================================
    # MATHEMATICAL SAFEGUARD: The Singularity Fix
    # ==============================================================
    # If norm is ~0, we are exactly at the geometric center of an obstacle.
    # Returning [0,0,0] destroys the Taylor constraint: 0*(x-p) + d - r >= 0.
    # We generate a random unit vector to "kick" the optimizer out of the saddle point.
    
    # Return a deterministic unit vector to ensure numerical invariance 
    # and line-search stability across successive SLSQP evaluations.
    deterministic_dir = np.array([1.0, 0.0, 0.0])
    return deterministic_dir