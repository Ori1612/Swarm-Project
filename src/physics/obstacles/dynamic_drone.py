import numpy as np
from src.physics.obstacles.base import Obstacle 

class DynamicDroneObstacle(Obstacle):

    def __init__(self, trajectory_matrix, radius):

        """
        trajectory_matrix: N x 3 numpy array. Can be truncated (N < T).
        radius: Physical radius of the drone.
        """

        self.trajectory_matrix = trajectory_matrix
        self.radius = radius

    def get_distance(self, point: np.ndarray, t: float = 0.0) -> float:
        
        # Matrix Truncation Support: If t exceeds the drone's flight time,
        # it mathematically "hovers" at its final coordinate.
        t_idx = min(int(t), len(self.trajectory_matrix) - 1)
        drone_pos = self.trajectory_matrix[t_idx]
        
        dist = np.linalg.norm(point - drone_pos)
        
        # Return distance to the surface of the drone
        return dist - self.radius