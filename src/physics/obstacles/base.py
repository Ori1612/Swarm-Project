from abc import ABC, abstractmethod
import numpy as np

class Obstacle(ABC):

    """
    Abstract Base Class for all Constructive Solid Geometry (CSG) objects.
    Every primitive or complex shape MUST implement the get_distance method.
    """
    
    @abstractmethod
    def get_distance(self, point: np.ndarray, t: float = 0.0) -> float:
        
        """
        Evaluates the Signed Distance Function (SDF) at a given 3D coordinate.
        
        Parameters:
        point (np.ndarray): A 1D array representing spatial coordinates [x, y, z].
        
        Returns:
        float: The shortest Euclidean distance to the obstacle boundary.
               > 0 means the point is strictly outside.
               = 0 means the point is exactly on the surface.
               < 0 means the point is inside the obstacle.
        """
        pass