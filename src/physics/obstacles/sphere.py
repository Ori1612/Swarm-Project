import numpy as np
from src.physics.obstacles.base import Obstacle

class Sphere(Obstacle):

    def __init__(self, center: np.ndarray, radius: float):

        """
        center: A 1D NumPy array [x, y, z] representing the sphere's origin.
        radius: A float representing the sphere's physical radius.
        """

        self.c = center
        self.r = radius

    def get_distance(self, point: np.ndarray, t: float = 0.0) -> float:
        return np.linalg.norm(point - self.c) - self.r

    def get_gradient(self, point: np.ndarray, t: float = 0.0) -> np.ndarray:
        diff = point - self.c
        dist = np.linalg.norm(diff)
        return diff / dist if dist > 1e-8 else np.array([1.0, 0.0, 0.0])