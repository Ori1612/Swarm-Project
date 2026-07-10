import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.animation import FuncAnimation
from skimage.measure import marching_cubes

class SDFEnvironmentRenderer:
    """
    Handles 3D Marching Cubes isosurface rendering of CSG obstacles, swarm animations,
    and visual proofs of 2D KKT dynamic tangent hyperplanes.
    """
    def __init__(self, bounds=((-10, 10), (-10, 10), (-10, 10)), resolution=50):
        self.bounds = bounds
        self.resolution = resolution

    def render_sdf_isosurface(self, ax, obstacle, t=0.0):
        """
        Extracts the zero-level isosurface (SDF = 0) across a 3D grid using Marching Cubes.
        Aligned with Ori's get_distance(point: np.ndarray, t: float) signature.
        """
        x = np.linspace(self.bounds[0][0], self.bounds[0][1], self.resolution)
        y = np.linspace(self.bounds[1][0], self.bounds[1][1], self.resolution)
        z = np.linspace(self.bounds[2][0], self.bounds[2][1], self.resolution)
        X, Y, Z = np.meshgrid(x, y, z, indexing='ij')

        grid_shape = X.shape
        sdf_grid = np.zeros(grid_shape)
        for i in range(grid_shape[0]):
            for j in range(grid_shape[1]):
                for k in range(grid_shape[2]):
                    point = np.array([X[i, j, k], Y[i, j, k], Z[i, j, k]])
                    sdf_grid[i, j, k] = obstacle.get_distance(point, t=t)

        try:
            verts, faces, _, _ = marching_cubes(sdf_grid, level=0.0)
            for idx, (min_val, max_val) in enumerate(self.bounds):
                verts[:, idx] = min_val + (verts[:, idx] / (self.resolution - 1)) * (max_val - min_val)

            mesh = Poly3DCollection(verts[faces], alpha=0.35, edgecolor='gray', linewidth=0.2)
            mesh.set_facecolor('cyan')
            ax.add_collection3d(mesh)
        except ValueError:
            pass

    def render_kkt_hyperplanes(self, ax, point, gradient, scale=2.0):
        """
        Visualizes the 2D tangent hyperplanes generated at the drone's position during SCP.
        """
        norm = np.linalg.norm(gradient)
        if norm < 1e-6:
            return
        normal = gradient / norm

        d = -np.dot(normal, point)
        xx, yy = np.meshgrid(
            np.linspace(point[0] - scale, point[0] + scale, 10),
            np.linspace(point[1] - scale, point[1] + scale, 10)
        )
        
        if abs(normal[2]) > 1e-5:
            zz = (-normal[0] * xx - normal[1] * yy - d) / normal[2]
            ax.plot_surface(xx, yy, zz, color='orange', alpha=0.5, rstride=1, cstride=1)

def animate_swarm_trajectories(trajectories, obstacle=None, bounds=((-10, 10), (-10, 10), (-10, 10)), save_path=None):
    """
    Animates N drones navigating R^3 space concurrently.
    Input: List of N trajectories, where each trajectory is a NumPy array of shape (T, 3).
    """
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    ax.set_xlim(bounds[0])
    ax.set_ylim(bounds[1])
    ax.set_zlim(bounds[2])
    ax.set_xlabel('X [m]')
    ax.set_ylabel('Y [m]')
    ax.set_zlabel('Z [m]')

    renderer = SDFEnvironmentRenderer(bounds=bounds)
    if obstacle is not None:
        renderer.render_sdf_isosurface(ax, obstacle)

    num_drones = len(trajectories)
    time_steps = trajectories[0].shape[0]

    colors = plt.cm.jet(np.linspace(0, 1, num_drones))
    lines = [ax.plot([], [], [], '-', color=colors[i], label=f'Drone {i+1}')[0] for i in range(num_drones)]
    points = [ax.plot([], [], [], 'o', color=colors[i], markersize=6)[0] for i in range(num_drones)]

    def update(t):
        for i in range(num_drones):
            traj = trajectories[i]
            lines[i].set_data(traj[:t+1, 0], traj[:t+1, 1])
            lines[i].set_3d_properties(traj[:t+1, 2])
            points[i].set_data([traj[t, 0]], [traj[t, 1]])
            points[i].set_3d_properties([traj[t, 2]])
        return lines + points

    anim = FuncAnimation(fig, update, frames=time_steps, interval=50, blit=False)
    
    if save_path:
        anim.save(save_path, writer='ffmpeg', fps=20)
    else:
        plt.legend()
        plt.show()
    return anim
