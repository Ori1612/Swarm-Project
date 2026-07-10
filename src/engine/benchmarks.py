import time

# ------------------------------------------------------------------
# HEADLESS RENDERING (Visualization / Gap Test Guide, Directive 2)
# The Agg backend MUST be selected before pyplot is imported so that
# long stress/gap tests never block on plt.show(). All figures are
# written straight to disk with bbox_inches='tight'.
# ------------------------------------------------------------------
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


class OptimizationDiagnostics:
    """
    Deep benchmarking suite tracking sub-optimality gaps, KKT residuals,
    and the dual-axis stress test analytics. All plotting is headless.
    """

    # =============================================================
    # Core metrics
    # =============================================================
    @staticmethod
    def calculate_path_length(trajectory):
        """Kinetic energy proxy / total path length: sum ||x_{t+1} - x_t||_2."""
        diffs = np.diff(trajectory, axis=0)
        return float(np.sum(np.linalg.norm(diffs, axis=1)))

    @classmethod
    def calculate_suboptimality_gap(cls, continuous_traj, discrete_cbs_traj):
        """Percentage difference between the continuous SCP path and the discrete CBS baseline."""
        scp_length = cls.calculate_path_length(continuous_traj)
        cbs_length = cls.calculate_path_length(discrete_cbs_traj)
        if cbs_length == 0:
            return 0.0
        return ((scp_length - cbs_length) / cbs_length) * 100.0

    # =============================================================
    # Gap Test analytics (Gap Test Guide, Section 4)
    # =============================================================
    @staticmethod
    def plot_resolution_vs_path_length(delta_x_values, cbs_lengths, scp_lengths, save_path):
        """Graph 1: Resolution vs. Path Length (The Asymptote)."""
        plt.figure(figsize=(8, 6))

        # CBS: jagged discrete grid path (starts high, asymptotes downward).
        plt.plot(delta_x_values, cbs_lengths, marker='o', color='red', label='CBS (Discrete Grid)')

        # SCP: the mathematically perfect continuous geodesic -> a flat horizontal line.
        scp_ref = float(np.nanmin(scp_lengths)) if len(scp_lengths) else 0.0
        plt.axhline(y=scp_ref, color='blue', linestyle='--', linewidth=2,
                    label='SCP (Continuous Geodesic)')

        plt.gca().invert_xaxis()  # read left->right as coarse (2.0) -> fine (0.2)
        plt.title('Sub-Optimality Gap: Resolution vs. Path Length')
        plt.xlabel(r'Grid Resolution $\Delta x$ (m)')
        plt.ylabel('Total Path Length (m)')
        plt.legend()
        plt.grid(True, linestyle=':', alpha=0.7)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

    @staticmethod
    def plot_resolution_vs_nodes_expanded(delta_x_values, nodes_expanded_values, save_path):
        """Graph 2: Resolution vs. Nodes Expanded (The Memory Wall) -- cubic explosion."""
        plt.figure(figsize=(8, 6))
        plt.plot(delta_x_values, nodes_expanded_values, marker='s', color='purple',
                 label='CBS A* Nodes Expanded')
        plt.gca().invert_xaxis()
        plt.yscale('log')  # cubic O(1/dx^3) blow-up reads clearly on a log axis
        plt.title('Memory Wall: Resolution vs. Nodes Expanded')
        plt.xlabel(r'Grid Resolution $\Delta x$ (m)')
        plt.ylabel('A* Nodes Expanded (log scale)')
        plt.legend()
        plt.grid(True, which='both', linestyle=':', alpha=0.7)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

    # =============================================================
    # Stress Test Phase 1 (Stress Test Guide, Section 3)
    # =============================================================
    @staticmethod
    def run_obstacle_scaling_benchmark(callback_factory, k_values, algorithms,
                                       trials=3, save_path="stress_phase1_failure_rate.png"):
        """
        Phase 1: Collision / Failure Rate (%) vs. Environmental Complexity (k obstacles).

        callback_factory(k, algorithm) -> run_trial(); run_trial() returns (success_bool, runtime).
        """
        results = {algo: [] for algo in algorithms}

        for k in k_values:
            print(f"  > Testing Complexity k={k}...")
            for algo in algorithms:
                run_trial = callback_factory(k, algo)
                failures = 0
                for _ in range(trials):
                    try:
                        success, _ = run_trial()
                    except Exception:
                        success = False
                    if not success:
                        failures += 1
                fail_rate = (failures / trials) * 100.0
                results[algo].append(fail_rate)

        plt.figure(figsize=(8, 6))
        colors = {'APF': 'red', 'SA': 'orange', 'SCP': 'blue'}
        for algo in algorithms:
            plt.plot(k_values, results[algo], marker='o',
                     color=colors.get(algo, 'black'), label=algo)
        plt.title('Phase 1: Collision / Failure Rate vs. Environmental Complexity')
        plt.xlabel('Number of Static CSG Obstacles ($k$)')
        plt.ylabel('Failure Rate (%)')
        plt.ylim(-5, 105)
        plt.legend()
        plt.grid(True, linestyle=':', alpha=0.7)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        return results

    # =============================================================
    # Stress Test Phase 2 (Stress Test Guide, Section 4)
    # =============================================================
    @staticmethod
    def run_swarm_scaling_benchmark(swarm_sizes, algorithms, callback_factory,
                                    save_path="stress_phase2_runtime.png", trials=1):
        """
        Phase 2: Computational Runtime (s) vs. Swarm Scale (N).

        callback_factory(N, algorithm) -> run_trial(); run_trial() returns (success_bool, runtime).
        Named distinctly from any legacy stress-test entry point to avoid signature clashes.
        """
        results_time = {algo: [] for algo in algorithms}

        for n in swarm_sizes:
            print(f"  > Testing Swarm Scale N={n}...")
            for algo in algorithms:
                run_trial = callback_factory(n, algo)
                total_time = 0.0
                for _ in range(trials):
                    try:
                        _, elapsed = run_trial()
                    except Exception:
                        elapsed = 0.0
                    total_time += elapsed
                results_time[algo].append(total_time / trials)

        plt.figure(figsize=(8, 6))
        colors = {'SA': 'orange', 'SCP': 'blue', 'APF': 'red'}
        for algo in algorithms:
            plt.plot(swarm_sizes, results_time[algo], marker='s',
                     color=colors.get(algo, 'black'), label=algo)
        plt.title('Phase 2: Computational Runtime vs. Swarm Scale')
        plt.xlabel('Swarm Scale ($N$ drones)')
        plt.ylabel('Average Runtime (s)')
        plt.legend()
        plt.grid(True, linestyle=':', alpha=0.7)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        return results_time

    # =============================================================
    # Optional extras: SCP convergence + 3D gap overlay (kept, now headless)
    # =============================================================
    @staticmethod
    def plot_convergence_tracking(residuals, save_path="scp_convergence.png"):
        """Graphs KKT stationarity residuals over SCP iterations (log scale)."""
        plt.figure(figsize=(8, 5))
        plt.plot(range(1, len(residuals) + 1), residuals, marker='o', linestyle='-', color='b')
        plt.yscale('log')
        plt.title('SCP Convergence: KKT Stationarity Residual over Iterations')
        plt.xlabel('SCP Iteration ($m$)')
        plt.ylabel(r'Stationarity Residual $||\nabla_X \mathcal{L}||_2$ (Log Scale)')
        plt.grid(True, which="both", ls="--", alpha=0.6)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

    @staticmethod
    def plot_gap_analysis(scp_traj, cbs_traj, save_path="gap_3d_overlay.png"):
        """Overlays the continuous SCP matrix and the discrete CBS matrix in 3D space."""
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        ax.plot(cbs_traj[:, 0], cbs_traj[:, 1], cbs_traj[:, 2],
                label='CBS (Discrete A* Grid)', color='red', linestyle='--', marker='s', markersize=4)
        ax.plot(scp_traj[:, 0], scp_traj[:, 1], scp_traj[:, 2],
                label='SCP (Continuous Linearization)', color='blue', linewidth=3)
        ax.set_title("Sub-Optimality Gap: Continuous vs. Discrete Optimization")
        ax.set_xlabel('X [m]'); ax.set_ylabel('Y [m]'); ax.set_zlabel('Z [m]')
        ax.legend()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()