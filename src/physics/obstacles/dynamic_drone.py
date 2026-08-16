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
        t_idx = min(int(t), len(self.trajectory_matrix) - 1)
        drone_pos = self.trajectory_matrix[t_idx]
        return np.linalg.norm(point - drone_pos) - self.radius

    def get_gradient(self, point: np.ndarray, t: float = 0.0) -> np.ndarray:
        t_idx = min(int(t), len(self.trajectory_matrix) - 1)
        drone_pos = self.trajectory_matrix[t_idx]
        diff = point - drone_pos
        dist = np.linalg.norm(diff)
        return diff / dist if dist > 1e-8 else np.array([1.0, 0.0, 0.0])