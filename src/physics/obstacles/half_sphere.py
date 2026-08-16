import numpy as np
from src.physics.obstacles.base import Obstacle 

class HalfSphere(Obstacle):

    def __init__(self, sphere: Obstacle, plane: Obstacle):

        """
        Takes instantiated Sphere and Plane objects to create a composite shape (Dome).
        """

        self.sphere = sphere
        self.plane = plane

    def get_distance(self, point: np.ndarray, t: float = 0.0) -> float:
        d_sphere = self.sphere.get_distance(point, t=t)
        d_plane = self.plane.get_distance(point, t=t)
        return max(d_sphere, -d_plane)

    def get_gradient(self, point: np.ndarray, t: float = 0.0) -> np.ndarray:
        d_sphere = self.sphere.get_distance(point, t=t)
        d_plane = self.plane.get_distance(point, t=t)
        return self.sphere.get_gradient(point, t=t) if d_sphere >= -d_plane else -self.plane.get_gradient(point, t=t)