import numpy as np
from src.physics.obstacles.base import Obstacle 

class Box(Obstacle):

    def __init__(self, center: np.ndarray, half_extents: np.ndarray):

        """
        center: A 1D array [x, y, z] representing the exact middle of the box.
        half_extents: A 1D array [bx, by, bz] representing half the width, depth, and height.
        """

        self.c = center
        self.b = half_extents

    def get_distance(self, point: np.ndarray, t: float = 0.0) -> float:
        q = np.abs(point - self.c) - self.b
        d_outside = np.linalg.norm(np.maximum(q, 0.0))
        d_inside = np.minimum(np.max(q), 0.0)
        return d_outside + d_inside

    def get_gradient(self, point: np.ndarray, t: float = 0.0) -> np.ndarray:
        diff = point - self.c
        q = np.abs(diff) - self.b
        sgn = np.where(diff >= 0, 1.0, -1.0)
        
        if np.any(q > 0):
            grad_unnorm = np.maximum(q, 0.0) * sgn
            norm = np.linalg.norm(grad_unnorm)
            return grad_unnorm / norm if norm > 1e-8 else np.array([1.0, 0.0, 0.0])
        else:
            idx = int(np.argmax(q))
            grad = np.zeros(3)
            grad[idx] = sgn[idx]
            return grad