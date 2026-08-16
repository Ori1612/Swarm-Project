import numpy as np
from src.physics.obstacles.base import Obstacle 

class Cylinder(Obstacle):

    def __init__(self, center: np.ndarray, radius: float, half_height: float):

        """
        center: A 1D array [x, y, z] representing the exact middle of the cylinder.
        """

        self.c = center
        self.r = radius
        self.h = half_height

    def get_distance(self, point: np.ndarray, t: float = 0.0) -> float:
        q_radial = np.linalg.norm(point[:2] - self.c[:2]) - self.r
        q_z = np.abs(point[2] - self.c[2]) - self.h
        q = np.array([q_radial, q_z])
        return np.minimum(np.max(q), 0.0) + np.linalg.norm(np.maximum(q, 0.0))

    def get_gradient(self, point: np.ndarray, t: float = 0.0) -> np.ndarray:
        diff_xy = point[:2] - self.c[:2]
        d_xy = np.linalg.norm(diff_xy)
        q_radial = d_xy - self.r
        diff_z = point[2] - self.c[2]
        q_z = np.abs(diff_z) - self.h
        
        n_xy = (diff_xy / d_xy) if d_xy > 1e-8 else np.array([1.0, 0.0])
        sgn_z = 1.0 if diff_z >= 0 else -1.0
        
        if q_radial > 0 and q_z > 0:
            vec2d = np.array([q_radial, q_z])
            vec2d_norm = np.linalg.norm(vec2d)
            return np.array([n_xy[0] * (q_radial / vec2d_norm), n_xy[1] * (q_radial / vec2d_norm), sgn_z * (q_z / vec2d_norm)])
        elif q_radial > q_z:
            return np.array([n_xy[0], n_xy[1], 0.0])
        else:
            return np.array([0.0, 0.0, sgn_z])