"""
guy/server.py  --  FastAPI backend for the Interactive 3D Swarm Dashboard
(Visualization Guide, Section 6).

Endpoints
  GET  /                      -> health check + scenario list
  GET  /scenario/{id}         -> CSG obstacle params + T x 3 trajectory matrices
  POST /kkt_query             -> scalar distance + gradient hyperplanes at a point

Run:
  uvicorn guy.server:app --reload      (from the project root)
  or simply:  python -m guy.server
"""

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.solvers.manager import SwarmManager
from src.engine.scenario_configs import build_scenario

app = FastAPI(title="Swarm Tactical Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trajectory horizon for the viewer. We dynamically scale VIZ_T based on the 
# environment bounds to keep drone speed constant.
BASE_VIZ_T = 15
BASE_ENV_SIZE = 20.0

# Default solver per scenario. Cyber-City is upgraded to SCP for high-fidelity
# trajectories. Other scenarios retain SA/APF for performance requirements as 
# per Stress Test specifications.
SCENARIO_SOLVER = {
    "cyber_city": "SCP",
    "torture_track": "SA",
    "csg_maze": "SA",
}

AVAILABLE_SCENARIOS = [
    "cyber_city", "torture_track", "csg_maze",
    "stress_phase1_k0", "stress_phase1_k2", "stress_phase1_k4",
    "stress_phase1_k6", "stress_phase1_k8",
]

# Caches so repeated hot-swaps don't recompute. Keyed by (scenario_id, solver).
_scenario_cache = {}
# The manager for the most recently loaded scenario (used by Math Mode queries).
active_manager = None


class KKTQuery(BaseModel):
    point: list[float]
    t: int = 0


def _make_crossing_drones(env, n=3, radius=0.5):
    """Generate N drones that cross the environment diagonally, scaled to its bounds."""
    lo = np.array(env.bounds[0], dtype=float)
    hi = np.array(env.bounds[1], dtype=float)
    span = hi - lo
    m = 0.05 * span            # keep starts/goals just inside the walls
    z_mid = (lo[2] + hi[2]) / 2.0

    # A few crossing corridors; extra drones reuse the pattern at slight Z offsets.
    patterns = [
        ([lo[0] + m[0], lo[1] + m[1], z_mid], [hi[0] - m[0], hi[1] - m[1], z_mid]),
        ([hi[0] - m[0], lo[1] + m[1], z_mid], [lo[0] + m[0], hi[1] - m[1], z_mid]),
        ([lo[0] + m[0], hi[1] - m[1], z_mid], [hi[0] - m[0], lo[1] + m[1], z_mid]),
    ]
    drones = []
    for i in range(n):
        start, goal = patterns[i % len(patterns)]
        dz = ((i // len(patterns)) * 0.1) * span[2]
        s = np.array(start, dtype=float); s[2] = min(hi[2] - m[2], s[2] + dz)
        g = np.array(goal, dtype=float);  g[2] = min(hi[2] - m[2], g[2] + dz)
        drones.append({'start': s, 'goal': g, 'radius': radius})
    return drones


def serialize_environment(env) -> list:
    """Extract raw geometry parameters from Ori's obstacle objects for the JS frontend."""
    serialized = []
    for obs in getattr(env, 'static_obstacles', []):
        name = type(obs).__name__
        if name == "Box":
            serialized.append({"type": "Box", "c": obs.c.tolist(), "b": obs.b.tolist()})
        elif name == "Sphere":
            serialized.append({"type": "Sphere", "c": obs.c.tolist(), "r": float(obs.r)})
        elif name == "Cylinder":
            serialized.append({"type": "Cylinder", "c": obs.c.tolist(),
                               "r": float(obs.r), "h": float(obs.h)})
        elif name == "HalfSphere":
            serialized.append({
                "type": "HalfSphere",
                "sphere": {"c": obs.sphere.c.tolist(), "r": float(obs.sphere.r)},
                "plane": {"p0": obs.plane.p0.tolist(), "n": obs.plane.n.tolist()},
            })
    return serialized


@app.get("/")
def root():
    return {"status": "ok", "scenarios": AVAILABLE_SCENARIOS}


@app.get("/scenario/{scenario_id}")
def get_scenario(scenario_id: str, solver: str | None = None):
    global active_manager

    try:
        env = build_scenario(scenario_id)
    except ValueError:
        return {"error": f"Invalid scenario id: {scenario_id}"}

    # Normalize solver type and validate
    solver_upper = solver.upper() if solver else "SA"
    
    if scenario_id == "torture_track":
        solver_type = solver_upper if solver_upper in ["SCP", "CBS", "BOTH"] else "SCP"
    else:
        solver_type = solver_upper if solver_upper in ["SCP", "SA"] else SCENARIO_SOLVER.get(scenario_id, "SA")

    # Always build a manager bound to a fresh env for Math Mode KKT queries.
    # Scale T dynamically: Larger spaces need more steps to maintain constant velocity.
    env_span = np.array(env.bounds[1]) - np.array(env.bounds[0])
    max_dim = np.max(env_span)
    dynamic_T = int(max(BASE_VIZ_T, (max_dim / BASE_ENV_SIZE) * BASE_VIZ_T))
    
    active_manager = SwarmManager(T=dynamic_T, environment=env)

    # Include dynamic_T in the cache key to prevent stale trajectory mismatches
    cache_key = (scenario_id, solver_type, dynamic_T)
    
    if cache_key in _scenario_cache:
        return _scenario_cache[cache_key]

    # Dynamically allocate swarm size based on Master Specifications
    labeled_trajectories = []
    
    if scenario_id == "torture_track":
        from src.solvers.cbs_solver import CBSSolver
        start_pos = np.array([16.0, 2.0, 5.0])
        goal_pos = np.array([2.0, 16.0, 5.0])
        drone_radius = 0.5
        
        # Normalize solver
        if solver_type not in ["SCP", "CBS", "BOTH"]:
            solver_type = "SCP"

        if solver_type in ["SCP", "BOTH"]:
            results = active_manager.solve_swarm(
                [{'start': start_pos, 'goal': goal_pos, 'radius': drone_radius}], 
                solver_type="SCP"
            )
            if results:
                for res in results:
                    labeled_trajectories.append({"solver": "SCP", "path": np.asarray(res).tolist()})
            
        if solver_type in ["CBS", "BOTH"]:
            cbs_solver = CBSSolver(env, radii={0: drone_radius}, grid_resolution=0.5, max_nodes=200000)
            cbs_result = cbs_solver.solve(start_positions={0: start_pos}, goal_positions={0: goal_pos})
            if cbs_result and len(cbs_result) > 0:
                cbs_raw = cbs_result[0]
                cbs_padded = np.zeros((dynamic_T, 3))
                for t in range(dynamic_T):
                    cbs_padded[t] = cbs_raw[min(t, len(cbs_raw) - 1)]
                labeled_trajectories.append({"solver": "CBS", "path": cbs_padded.tolist()})
        
        # Final fallback
        if len(labeled_trajectories) == 0:
            results = active_manager.solve_swarm(
                [{'start': start_pos, 'goal': goal_pos, 'radius': drone_radius}], 
                solver_type="SCP"
            )
            if results:
                for res in results:
                    labeled_trajectories.append({"solver": "SCP", "path": np.asarray(res).tolist()})
        
    else:
        if scenario_id.startswith("stress_phase1"):
            swarm_size = 4
        elif scenario_id == "csg_maze":
            swarm_size = 10
        elif scenario_id == "cyber_city":
            swarm_size = 5
        else:
            swarm_size = 3

        drones = _make_crossing_drones(env, n=swarm_size, radius=0.5)
        trajectories = active_manager.solve_swarm(drones, solver_type=solver_type)
        labeled_trajectories = [{"solver": solver_type, "path": np.asarray(t).tolist()} for t in trajectories]

    # NOTE: call export helper with a real path, OR (as here) serialize inline to
    # avoid writing a file on every request.
    print(f"DEBUG: Trajectories Count: {len(labeled_trajectories)}")

    payload = {
        "scenario": scenario_id,
        "solver": solver_type,
        "bounds": [list(env.bounds[0]), list(env.bounds[1])],
        "obstacles": serialize_environment(env),
        "trajectories": labeled_trajectories,
    }
    _scenario_cache[cache_key] = payload
    return payload


@app.post("/kkt_query")
def kkt_query(query: KKTQuery):
    if active_manager is None:
        return {"error": "No active scenario loaded."}
    hyperplanes = active_manager.query_kkt_hyperplanes(query.point, t=query.t)
    return {"hyperplanes": hyperplanes}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
