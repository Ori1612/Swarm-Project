import os
import sys
import numpy as np

from src.engine.scenario_configs import build_scenario, get_scenario_drone_radius
from src.engine.server import get_scenario

SCENARIOS = [
    ("1", "Cyber City", "cyber_city", ["SCP"]),
    ("2", "Torture Track", "torture_track", ["SCP", "CBS", "BOTH"]),
    ("3", "CSG Maze", "csg_maze", ["SA", "SCP"]),
    ("4", "Stress Test Phase 1 (k=0)", "stress_phase1_k0", ["APF", "SA", "SCP"]),
    ("5", "Stress Test Phase 1 (k=2)", "stress_phase1_k2", ["APF", "SA", "SCP"]),
    ("6", "Stress Test Phase 1 (k=4)", "stress_phase1_k4", ["APF", "SA", "SCP"]),
    ("7", "Stress Test Phase 1 (k=6)", "stress_phase1_k6", ["APF", "SA", "SCP"]),
    ("8", "Stress Test Phase 1 (k=8)", "stress_phase1_k8", ["APF", "SA", "SCP"]),
]


def print_trajectory_matrix(drone_idx: int, path: np.ndarray, name: str = ""):
    print(f"\n{'=' * 75}")
    title = f"TRAJECTORY MATRIX: Drone {drone_idx + 1}" + (f" ({name})" if name else "")
    print(f" {title.center(71)} ")
    print(f"{'=' * 75}")
    print("  Step  |      X (m)     |      Y (m)     |      Z (m)     | Velocity (m/s) ")
    print("-" * 75)
    for t in range(len(path)):
        vel = 0.0 if t == 0 else np.linalg.norm(path[t] - path[t - 1])
        print(f"   {t:02d}   |   {path[t][0]:10.4f}   |   {path[t][1]:10.4f}   |   {path[t][2]:10.4f}   |   {vel:10.4f}")
    print("-" * 75)


def audit_trajectories():
    print("\n" + "=" * 75)
    print("        SWARM TRAJECTORY AUDITOR & COLLISION DETECTOR")
    print("=" * 75)
    print("Select a Scenario:")
    for num, label, _, _ in SCENARIOS:
        print(f"  [{num}] {label}")
    print("=" * 75)

    choice = input("\nEnter choice [1-8] (default 1): ").strip()
    selected = next((s for s in SCENARIOS if s[0] == choice), SCENARIOS[0])
    _, label, scenario_id, solvers = selected

    print(f"\nSelected: {label}")
    solver = solvers[0]
    if len(solvers) > 1:
        print(f"Available solvers: {', '.join(solvers)}")
        solver_input = input(f"Choose solver [{'/'.join(solvers)}] (default {solvers[0]}): ").strip().upper()
        if solver_input in solvers:
            solver = solver_input

    print(f"\nLoading payload for '{scenario_id}' using solver '{solver}'...")
    payload = get_scenario(scenario_id, solver=solver)

    if not payload or "trajectories" not in payload or len(payload["trajectories"]) == 0:
        print("[!] Error: No trajectories found in payload.")
        return

    trajectories = [np.array(t["path"]) for t in payload["trajectories"]]
    drone_names = [t.get("solver", f"Drone {i+1}") for i, t in enumerate(payload["trajectories"])]
    env = build_scenario(scenario_id)

    drone_radius = payload.get("drone_radius", get_scenario_drone_radius(scenario_id))
    min_separation = 2 * drone_radius

    num_drones = len(trajectories)
    T = min(len(t) for t in trajectories)

    print("\n" + "=" * 75)
    print(f" AUDITING SCENARIO: {label.upper()} | SOLVER: {solver}")
    print(f" Drones: {num_drones} | Temporal Horizon T: {T} steps | Physical Radius: {drone_radius:.2f}m")
    print("=" * 75)

    # ---------------------------------------------------------
    # 1. Static Obstacle Penetration Audit
    # ---------------------------------------------------------
    print("\n[1/2] STATIC CSG OBSTACLE CLEARANCE AUDIT")
    print("-" * 75)
    obstacle_violations = []
    min_obs_clearance = {i: float('inf') for i in range(num_drones)}

    for d_idx, path in enumerate(trajectories):
        for t in range(len(path)):
            pt = path[t]
            dist_to_surface = env.get_distance(pt)
            clearance = dist_to_surface - drone_radius

            if clearance < min_obs_clearance[d_idx]:
                min_obs_clearance[d_idx] = clearance

            # Strict threshold with numerical epsilon
            if clearance < -1e-4:
                obstacle_violations.append({
                    "drone": d_idx + 1,
                    "name": drone_names[d_idx],
                    "t": t,
                    "pos": pt,
                    "dist": dist_to_surface,
                    "penetration": abs(clearance)
                })

    if not obstacle_violations:
        print("  -> PASSED: All drones maintain strict physical clearance from all obstacles.")
        for d_idx in range(num_drones):
            name_str = f" ({drone_names[d_idx]})" if drone_names[d_idx] else ""
            print(f"     Drone {d_idx + 1}{name_str}: Minimum Obstacle Clearance = {min_obs_clearance[d_idx]:.4f} m")
    else:
        print(f"  -> [!] FAILED: Detected {len(obstacle_violations)} obstacle penetration steps:")
        for v in obstacle_violations:
            pos_str = f"[{v['pos'][0]:.2f}, {v['pos'][1]:.2f}, {v['pos'][2]:.2f}]"
            print(f"     * Drone {v['drone']} ({v['name']}) at t={v['t']:02d} | Pos: {pos_str} | Penetration Depth: {v['penetration']:.4f} m")

    # ---------------------------------------------------------
    # 2. Inter-Drone Dynamic Separation Audit
    # ---------------------------------------------------------
    print("\n[2/2] INTER-DRONE DYNAMIC SEPARATION AUDIT")
    print("-" * 75)
    if num_drones < 2:
        print("  -> Single-drone mission: Inter-drone collision checks skipped.")
    else:
        swarm_violations = []
        min_swarm_dist = float('inf')
        min_pair = (1, 2)
        min_t = 0

        for t in range(T):
            for i in range(num_drones):
                for j in range(i + 1, num_drones):
                    p1 = trajectories[i][t]
                    p2 = trajectories[j][t]
                    dist = np.linalg.norm(p1 - p2)

                    if dist < min_swarm_dist:
                        min_swarm_dist = dist
                        min_pair = (i + 1, j + 1)
                        min_t = t

                    if dist < (min_separation - 1e-4):
                        swarm_violations.append({
                            "t": t,
                            "d1": i + 1,
                            "d2": j + 1,
                            "name1": drone_names[i],
                            "name2": drone_names[j],
                            "p1": p1,
                            "p2": p2,
                            "dist": dist,
                            "overlap": min_separation - dist
                        })

        if not swarm_violations:
            print(f"  -> PASSED: Zero inter-drone collisions detected across all {T} time steps.")
            print(f"     Closest approach: {min_swarm_dist:.4f} m (Threshold: {min_separation:.2f} m) between Drone {min_pair[0]} & Drone {min_pair[1]} at t={min_t:02d}.")
        else:
            print(f"  -> [!] FAILED: Detected {len(swarm_violations)} inter-drone collision events:")
            for c in swarm_violations:
                print(f"     * t={c['t']:02d}: Drone {c['d1']} ({c['name1']}) <-> Drone {c['d2']} ({c['name2']}) | Dist: {c['dist']:.4f} m (Overlap: {c['overlap']:.4f} m)")

    print("\n" + "=" * 75)

    # ---------------------------------------------------------
    # Optional Detailed Trajectory Table Inspection
    # ---------------------------------------------------------
    inspect = input("\nWould you like to print full coordinate matrices? [y/N]: ").strip().lower()
    if inspect == 'y':
        for i, traj in enumerate(trajectories):
            print_trajectory_matrix(i, traj, drone_names[i])


if __name__ == "__main__":
    audit_trajectories()