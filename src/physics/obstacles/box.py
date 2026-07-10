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

        """
        Calculates the Signed Distance to the box.
        Formula: ||max(q, 0)||_2 + min(max(qx, qy, qz), 0)
        """
        
        # Step 1: Translate point to local space and fold into the first quadrant
        q = np.abs(point - self.c) - self.b
        
        # Step 2: The Outside Distance
        # np.maximum(q, 0.0) is an element-wise operation. It compares each element 
        # in q to 0.0 and keeps the larger value, zeroing out the negative interior components.
        d_outside = np.linalg.norm(np.maximum(q, 0.0))
        
        # Step 3: The Inside Distance
        # np.max(q) is an array-wide operation. It finds the single largest scalar value in the entire array q.
        # np.minimum(..., 0.0) ensures this only triggers if the drone is actually inside (where the max is still negative).
        d_inside = np.minimum(np.max(q), 0.0)
        
        # Step 4: Combine for the final Signed Distance
        return d_outside + d_inside