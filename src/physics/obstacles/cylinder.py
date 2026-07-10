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
        
        # 1. Radial offset (XY plane)
        q_radial = np.linalg.norm(point[:2] - self.c[:2]) - self.r
        
        # 2. Axial offset (Z axis)
        q_z = np.abs(point[2] - self.c[2]) - self.h
        
        # 3. Pack into our 2D offset vector
        q = np.array([q_radial, q_z])
        
        # 4. Dimension-agnostic AABB logic
        d_inside = np.minimum(np.max(q), 0.0)
        d_outside = np.linalg.norm(np.maximum(q, 0.0))
        
        return d_inside + d_outside