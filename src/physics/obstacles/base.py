from abc import ABC, abstractmethod
import numpy as np

class Obstacle(ABC):

    """
    Abstract Base Class for all Constructive Solid Geometry (CSG) objects.
    Every primitive or complex shape MUST implement the get_distance method.
    """
    
    @abstractmethod
    def get_distance(self, point: np.ndarray, t: float = 0.0) -> float:
        pass

    def get_gradient(self, point: np.ndarray, t: float = 0.0) -> np.ndarray:
        """
        Analytical spatial gradient ∇SDF(p). Defaults to numerical fallback if unspecialized.
        """
        h = 1e-5
        I = np.eye(3)
        grad = np.zeros(3)
        for i in range(3):
            d_plus = self.get_distance(point + h * I[i], t=t)
            d_minus = self.get_distance(point - h * I[i], t=t)
            grad[i] = (d_plus - d_minus) / (2 * h)
        norm = np.linalg.norm(grad)
        return grad / norm if norm > 1e-8 else np.array([1.0, 0.0, 0.0])