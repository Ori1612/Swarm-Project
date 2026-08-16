import numpy as np
from src.physics.obstacles.base import Obstacle

def approximate_gradient(point: np.ndarray, obstacle: Obstacle, t: float = 0.0, h: float = 1e-5) -> np.ndarray:
    """
    Evaluates the exact analytical normalized spatial gradient ∇SDF in O(1).
    Falls back to central finite differences only if unspecialized.
    """
    if hasattr(obstacle, 'get_gradient'):
        return obstacle.get_gradient(point, t=t)

    grad = np.zeros(3)
    I = np.eye(3)
    for i in range(3):
        d_plus = obstacle.get_distance(point + h * I[i], t=t)
        d_minus = obstacle.get_distance(point - h * I[i], t=t)
        grad[i] = (d_plus - d_minus) / (2 * h)

    norm = np.linalg.norm(grad)
    return grad / norm if norm > 1e-8 else np.array([1.0, 0.0, 0.0])