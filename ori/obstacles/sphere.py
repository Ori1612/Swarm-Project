import numpy as np
from ori.obstacles.base import Obstacle

class Sphere(Obstacle):

    def __init__(self, center: np.ndarray, radius: float):

        """
        center: A 1D NumPy array [x, y, z] representing the sphere's origin.
        radius: A float representing the sphere's physical radius.
        """

        self.c = center
        self.r = radius

    def get_distance(self, point: np.ndarray, t: float = 0.0) -> float:

        """
        Calculates the Signed Distance from the spatial coordinate 'point' to the sphere boundary.
        """
        
        return np.linalg.norm(point - self.c) - self.r