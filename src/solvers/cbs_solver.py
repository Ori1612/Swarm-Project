import numpy as np
import heapq
import itertools
import copy

# ==========================================
# LOW-LEVEL: 4D A* ENGINE
# ==========================================

class Node:
    def __init__(self, state, g=0.0, h=0.0, parent=None):
        self.state = state     # Natively a 4D np.array([x, y, z, t])
        self.g = g
        self.h = h
        self.f = g + h
        self.parent = parent

    def __lt__(self, other):
        # The metric for the Min-Heap priority queue
        return self.f < other.f

def get_neighbors(current_node, grid_resolution, static_grid, env_bounds, constraints, drone_radius):
    neighbors = []
    r = grid_resolution
    movements = list(itertools.product([-r, 0.0, r], repeat=3))

    for move in movements:
        new_state = current_node.state.copy()
        new_state[:3] += move
        new_state[3] += 1.0

        # FIX 1: Strict mathematical bound to prevent infinite state space explosion
        if new_state[3] > 1000.0:
            continue

        spatial_dist = np.linalg.norm(np.array(move))
        
        # FIX 2: Force the A* heuristic to treat time-steps equally to spatial steps
        step_cost = grid_resolution if spatial_dist == 0.0 else spatial_dist

        # Filter 1: Discrete O(1) Matrix Lookup
        ix = int(np.floor((new_state[0] - env_bounds[0][0]) / grid_resolution + 1e-9))
        iy = int(np.floor((new_state[1] - env_bounds[0][1]) / grid_resolution + 1e-9))
        iz = int(np.floor((new_state[2] - env_bounds[0][2]) / grid_resolution + 1e-9))

        # Check if out of physical bounds, or if the grid cell is a solid wall
        if (0 <= ix < static_grid.shape[0] and
            0 <= iy < static_grid.shape[1] and
            0 <= iz < static_grid.shape[2]):

            if static_grid[ix, iy, iz]:
                continue
        else:
            continue

        # Filter 2: Volumetric CBS Drone-to-Drone Collision
        collision = False
        t_key = int(new_state[3])
        for forbidden_pos, min_dist in constraints.get(t_key, []):
            if np.linalg.norm(new_state[:3] - forbidden_pos) < min_dist:
                collision = True
                break

        if collision:
            continue

        neighbors.append((new_state, step_cost))

    return neighbors

def run_4D_A_star(start_pos, goal_pos, grid_resolution, static_grid, env_bounds, constraints, drone_radius,
                  stats=None, max_nodes=None, heuristic_weight=1.0):
    open_set = []
    closed_set = set()
    spatial_closed = set()
    use_spatial = not constraints

    def cell_of(state):
        return (int(np.floor((state[0] - env_bounds[0][0]) / grid_resolution + 1e-9)),
                int(np.floor((state[1] - env_bounds[0][1]) / grid_resolution + 1e-9)),
                int(np.floor((state[2] - env_bounds[0][2]) / grid_resolution + 1e-9)))

    start_state = np.append(start_pos, 0.0)
    start_h = heuristic_weight * np.linalg.norm(start_pos - goal_pos)
    heapq.heappush(open_set, Node(state=start_state, g=0.0, h=start_h))

    expanded = 0
    while open_set:
        current_node = heapq.heappop(open_set)

        if use_spatial:
            key = cell_of(current_node.state)
            if key in spatial_closed:
                continue
            spatial_closed.add(key)
        else:
            key = tuple(current_node.state)
            if key in closed_set:
                continue
            closed_set.add(key)

        expanded += 1
        if stats is not None:
            stats['expanded'] = stats.get('expanded', 0) + 1
        if max_nodes is not None and expanded > max_nodes:
            return None

        # 1. Termination Check
        if np.linalg.norm(current_node.state[:3] - goal_pos) < (grid_resolution / 2.0):
            trajectory = []
            while current_node is not None:
                trajectory.append(current_node.state[:3])
                current_node = current_node.parent
            trajectory.reverse()
            return np.array(trajectory)

        # 2. Expand Neighbors
        neighbors = get_neighbors(current_node, grid_resolution, static_grid, env_bounds, constraints, drone_radius)
        for next_state, step_cost in neighbors:
            if use_spatial:
                if cell_of(next_state) in spatial_closed:
                    continue
            else:
                if tuple(next_state) in closed_set:
                    continue
            g_new = current_node.g + step_cost
            h_new = heuristic_weight * np.linalg.norm(next_state[:3] - goal_pos)
            heapq.heappush(open_set, Node(state=next_state, g=g_new, h=h_new, parent=current_node))

    return None

# ==========================================
# HIGH-LEVEL: CBS MASTER MANAGER
# ==========================================

class CTNode:
    def __init__(self, constraints=None, solution=None):
        self.constraints = constraints if constraints else {}
        self.solution = solution if solution else {}
        self.cost = 0.0

    def calculate_cost(self):
        self.cost = sum(len(path) for path in self.solution.values())

    def __lt__(self, other):
        return self.cost < other.cost

class CBSSolver:
    def __init__(self, environment, radii, grid_resolution=1.0, max_nodes=None):
        self.env = environment
        self.radii = radii
        self.resolution = grid_resolution
        self.static_grid = None
        self.astar_nodes_expanded = 0
        self.max_nodes = max_nodes
        self._search_stats = {'expanded': 0}
        self.discretize_environment()

    def detect_first_collision(self, solution):
        drone_ids = list(solution.keys())
        max_t = max(len(path) for path in solution.values())

        path_lengths = {d_id: len(solution[d_id]) for d_id in drone_ids}
        for t in range(max_t):
            for i in range(len(drone_ids)):
                for j in range(i + 1, len(drone_ids)):
                    d1 = drone_ids[i]
                    d2 = drone_ids[j]

                    pos1 = solution[d1][min(t, path_lengths[d1] - 1)]
                    pos2 = solution[d2][min(t, path_lengths[d2] - 1)]

                    min_distance = self.radii[d1] + self.radii[d2]

                    if np.linalg.norm(pos1 - pos2) < min_distance:
                        return (d1, d2, pos1, pos2, t)
        return None

    def solve(self, start_positions, goal_positions):
        print("Initializing CBS Swarm Manager...")
        self._search_stats = {'expanded': 0}
        root = CTNode()
        drone_ids = list(start_positions.keys())

        for d_id in drone_ids:
            root.constraints[d_id] = {}

        for d_id in drone_ids:
            print(f"Calculating initial path for Drone {d_id}...")
            path = run_4D_A_star(
                start_positions[d_id], goal_positions[d_id],
                self.resolution, self.static_grid, self.env.bounds,
                root.constraints[d_id], self.radii[d_id],
                stats=self._search_stats, max_nodes=self.max_nodes
            )
            self.astar_nodes_expanded = self._search_stats['expanded']
            if path is None:
                print(f"FATAL: No path exists for Drone {d_id}. Target is walled off.")
                return None
            root.solution[d_id] = path

        root.calculate_cost()

        tree = []
        heapq.heappush(tree, root)

        nodes_expanded = 0
        while tree:
            best_node = heapq.heappop(tree)
            nodes_expanded += 1

            collision = self.detect_first_collision(best_node.solution)

            if collision is None:
                print(f"CBS Complete! Global minimum found. Nodes expanded: {nodes_expanded}")

                final_solution = []
                max_t = max(len(path) for path in best_node.solution.values())
                for d_id in sorted(drone_ids):
                    path = best_node.solution[d_id]
                    if len(path) < max_t:
                        padding = np.tile(path[-1], (max_t - len(path), 1))
                        path = np.vstack((path, padding))
                    final_solution.append(path)
                return final_solution

            d1, d2, pos1, pos2, t = collision
            print(f"Collision detected between Drone {d1} and {d2} at t={t}")

            min_dist = self.radii[d1] + self.radii[d2]

            for fix_drone, avoid_pos in [(d1, pos2), (d2, pos1)]:
                child = CTNode(
                    constraints=copy.deepcopy(best_node.constraints),
                    solution=copy.deepcopy(best_node.solution)
                )

                if t not in child.constraints[fix_drone]:
                    child.constraints[fix_drone][t] = []

                child.constraints[fix_drone][t].append((avoid_pos, min_dist))

                new_path = run_4D_A_star(
                    start_positions[fix_drone], goal_positions[fix_drone],
                    self.resolution, self.static_grid, self.env.bounds,
                    child.constraints[fix_drone], self.radii[fix_drone],
                    stats=self._search_stats, max_nodes=self.max_nodes
                )
                self.astar_nodes_expanded = self._search_stats['expanded']

                if new_path is not None:
                    child.solution[fix_drone] = new_path
                    child.calculate_cost()
                    heapq.heappush(tree, child)

        print("CBS Search Space Exhausted. No valid swarm paths found.")
        return None

    def discretize_environment(self):
        print("Pre-computing SDF Environment Bridge...")

        x_min, y_min, z_min = self.env.bounds[0]
        x_max, y_max, z_max = self.env.bounds[1]

        nx = int((x_max - x_min) / self.resolution) + 1
        ny = int((y_max - y_min) / self.resolution) + 1
        nz = int((z_max - z_min) / self.resolution) + 1

        self.static_grid = np.zeros((nx, ny, nz), dtype=bool)

        x_coords = np.linspace(x_min, x_max, nx)
        y_coords = np.linspace(y_min, y_max, ny)
        z_coords = np.linspace(z_min, z_max, nz)

        # Voxel corner offsets to prevent corner-cutting (more conservative)
        offsets = [-self.resolution/2, 0, self.resolution/2]
        
        for i, x in enumerate(x_coords):
            for j, y in enumerate(y_coords):
                for k, z in enumerate(z_coords):
                    # Check center + boundary to ensure obstacle solidity
                    is_blocked = False
                    for dx in offsets:
                        for dy in offsets:
                            for dz in offsets:
                                pos = np.array([x + dx, y + dy, z + dz])
                                max_radius = max(self.radii.values()) if self.radii else 0.0
                                if self.env.get_distance(pos) <= max_radius:
                                    is_blocked = True
                                    break
                            if is_blocked: break
                        if is_blocked: break
                    
                    self.static_grid[i, j, k] = is_blocked