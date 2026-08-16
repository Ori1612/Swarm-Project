import numpy as np
from src.physics.obstacles.base import Obstacle

class Plane(Obstacle):

    def __init__(self, p0: np.ndarray, normal: np.ndarray):

        """
        p0: A known 3D coordinate on the surface of the plane.
        normal: The orthogonal direction the plane faces.
        """

        self.p0 = p0
        # We must mathematically guarantee the normal is a unit vector (length 1)
        # otherwise the dot product will scale the distance incorrectly.
        self.n = normal / np.linalg.norm(normal)

    def get_distance(self, point: np.ndarray, t: float = 0.0) -> float:
        return (point - self.p0) @ self.n

    def get_gradient(self, point: np.ndarray, t: float = 0.0) -> np.ndarray:
        return self.n

