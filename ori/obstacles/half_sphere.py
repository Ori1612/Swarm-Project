import numpy as np
from ori.obstacles.base import Obstacle 

class HalfSphere(Obstacle):

    def __init__(self, sphere: Obstacle, plane: Obstacle):

        """
        Takes instantiated Sphere and Plane objects to create a composite shape (Dome).
        """

        self.sphere = sphere
        self.plane = plane

    def get_distance(self, point: np.ndarray, t: float = 0.0) -> float:

        """
        Evaluates the SDF of the Half-Sphere.
        """
        
        d_sphere = self.sphere.get_distance(point)
        d_plane = self.plane.get_distance(point)
        
        # CSG Intersection: The plane normal points INTO the solid half-sphere.
        # To make the interior negative (standard SDF), we must invert the plane distance.
        return max(d_sphere, -d_plane)