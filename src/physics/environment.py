import numpy as np

class Environment:
    def __init__(self, room_bounds=([0.0, 0.0, 0.0], [10.0, 10.0, 10.0])):
        # Define the absolute physical limits of the CSG space
        self.bounds = room_bounds
        self.static_obstacles = []
        self.dynamic_obstacles = []

    def add_static_obstacle(self, obstacle):
        self.static_obstacles.append(obstacle)

    def add_dynamic_obstacle(self, obstacle):
        self.dynamic_obstacles.append(obstacle)

    def get_distance(self, point: np.ndarray, t: float = 0.0) -> float:

        """
        Used by APF & SA.
        Returns the absolute minimum scalar distance to the closest surface.
        """

        distances = []

        for obs in self.static_obstacles + self.dynamic_obstacles:
            distances.append(obs.get_distance(point, t=t))
        
        if not distances:
            return float('inf')
        
        return min(distances)

    def get_nearby_obstacles(self, point: np.ndarray, t: float = 0.0, detection_radius: float = 5.0):

        """
        Used strictly by SCP.
        Returns a list of all obstacles within the Trust Region buffer, 
        allowing SCP to build simultaneous KKT hyperplanes.
        """

        nearby = []
        for obs in self.static_obstacles + self.dynamic_obstacles:
            if obs.get_distance(point, t=t) <= detection_radius:
                nearby.append(obs)
        return nearby