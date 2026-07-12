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
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import os
import json
import threading
from src.solvers.manager import SwarmManager
from src.engine.scenario_configs import build_scenario

CACHE_DIR = "cache_data"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

app = FastAPI(title="Swarm Tactical Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Trajectory horizon for the viewer. We dynamically scale VIZ_T based on the
# environment bounds to keep drone speed constant.
BASE_VIZ_T = 15
BASE_ENV_SIZE = 20.0

# Default solver per scenario. Cyber-City is upgraded to SCP for high-fidelity
# trajectories. Other scenarios are strictly aligned with the Benchmarking Specifications.
SCENARIO_SOLVER = {
    "cyber_city": "SCP",
    "torture_track": "SCP",    # Gap Test: SCP vs CBS [cite: 48, 51]
    "csg_maze": "SA",          # Phase 2: SA vs SCP (APF excluded) [cite: 31]
}

# Explicit time horizon steps mapping to maintain strict scientific control metrics
SCENARIO_T = {
    "cyber_city": 75,
    "torture_track": 20,
    "csg_maze": 30,
}

AVAILABLE_SCENARIOS = [
    "cyber_city", "torture_track", "csg_maze",
    "stress_phase1_k0", "stress_phase1_k2", "stress_phase1_k4",
    "stress_phase1_k6", "stress_phase1_k8",
]

# Caches so repeated hot-swaps don't recompute. Keyed by (scenario_id, solver).
_scenario_cache = {}
# Granular thread locks map to prevent concurrent optimization compute races
_scenario_locks = {}
_locks_master_lock = threading.Lock()

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


@app.get("/api/health")
def health_check():
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
    elif scenario_id.startswith("stress_phase1"):
        # Phase 1: Must evaluate APF, SA, SCP [cite: 20]
        solver_type = solver_upper if solver_upper in ["APF", "SA", "SCP"] else "APF"
    else:
        solver_type = solver_upper if solver_upper in ["SA", "SCP"] else SCENARIO_SOLVER.get(scenario_id, "SA")

    # Always build a manager bound to a fresh env for Math Mode KKT queries.
    if scenario_id in SCENARIO_T:
        dynamic_T = SCENARIO_T[scenario_id]
    elif scenario_id.startswith("stress_phase1"):
        dynamic_T = 30
    else:
        env_span = np.array(env.bounds[1]) - np.array(env.bounds[0])
        max_dim = np.max(env_span)
        dynamic_T = int(max(BASE_VIZ_T, (max_dim / BASE_ENV_SIZE) * BASE_VIZ_T))
    
    active_manager = SwarmManager(T=dynamic_T, environment=env)

    # Include dynamic_T in the cache key to prevent stale trajectory mismatches
    cache_key = (scenario_id, solver_type, dynamic_T)
    cache_file = os.path.join(CACHE_DIR, f"payload_{scenario_id}_{solver_type}_{dynamic_T}.json")
    
    # Thread-safe retrieval or instantiation of a lock dedicated to this specific computation
    with _locks_master_lock:
        if cache_key not in _scenario_locks:
            _scenario_locks[cache_key] = threading.Lock()
        scenario_lock = _scenario_locks[cache_key]

    # Block any concurrent incoming request for the exact same scenario/solver configuration
    with scenario_lock:
        if cache_key in _scenario_cache:
            print(f"DEBUG: Concurrent request resolved via memory cache for {scenario_id}.")
            return _scenario_cache[cache_key]
            
        if os.path.exists(cache_file):
            print(f"DEBUG: Concurrent request resolved via disk cache loading for {scenario_id} ({solver_type})...")
            with open(cache_file, 'r') as f:
                payload = json.load(f)
            _scenario_cache[cache_key] = payload
            return payload

        # Intercept single solver requests by reusing the complete BOTH cache if available
        if scenario_id == "torture_track" and solver_type in ["SCP", "CBS"]:
            both_key = (scenario_id, "BOTH", dynamic_T)
            both_file = os.path.join(CACHE_DIR, f"payload_{scenario_id}_BOTH_{dynamic_T}.json")
            both_payload = None
            
            if both_key in _scenario_cache:
                both_payload = _scenario_cache[both_key]
            elif os.path.exists(both_file):
                print(f"DEBUG: Slicing single trajectory from BOTH disk cache for {solver_type}...")
                with open(both_file, 'r') as f:
                    both_payload = json.load(f)
                _scenario_cache[both_key] = both_payload
                
            if both_payload:
                filtered_trajectories = [t for t in both_payload["trajectories"] if t["solver"].upper() == solver_type]
                payload = dict(both_payload)
                payload["solver"] = solver_type
                payload["trajectories"] = filtered_trajectories
                _scenario_cache[cache_key] = payload
                return payload

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
            # FIX: Build a fresh environment so the SCP drone isn't seen as a blocking obstacle!
            cbs_env = build_scenario(scenario_id)
            cbs_solver = CBSSolver(cbs_env, radii={0: drone_radius}, grid_resolution=0.5, max_nodes=200000)
            cbs_result = cbs_solver.solve(start_positions={0: start_pos}, goal_positions={0: goal_pos})
            if cbs_result and len(cbs_result) > 0:
                # FIX: Do not truncate CBS to dynamic_T. Keep its true voxel-step length.
                labeled_trajectories.append({"solver": "CBS", "path": np.asarray(cbs_result[0]).tolist()})
        
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
            # Phase 1: Engineered Head-On Dynamic Crucible. D1/D2 deploy left, D3/D4 deploy right.
            # Forces a 4-way cross-traffic intersection directly over the non-convex traps at X=10.
            drones = [
                {'start': np.array([2.0, 6.5, 12.0]),  'goal': np.array([18.0, 13.5, 8.0]),  'radius': 0.5},
                {'start': np.array([2.0, 13.5, 8.0]),  'goal': np.array([18.0, 6.5, 12.0]),  'radius': 0.5},
                {'start': np.array([18.0, 6.5, 8.0]),  'goal': np.array([2.0, 13.5, 12.0]),  'radius': 0.5},
                {'start': np.array([18.0, 13.5, 12.0]), 'goal': np.array([2.0, 6.5, 8.0]),   'radius': 0.5},
            ]
        elif scenario_id == "csg_maze":
            # Phase 2: Structural Funnel Matrix. Distributes up to 10 drones into safe 
            # channels while setting up counter-directional cross-traffic at the cylinder mouth.
            swarm_size = 10
            drones = []
            for i in range(swarm_size):
                y_start = 8.0 if i % 2 == 0 else 12.0
                y_goal = 12.0 if i % 2 == 0 else 8.0
                z_pos = 4.0 + (i // 2) * 3.0
                drones.append({
                    'start': np.array([2.0, y_start, z_pos]),
                    'goal': np.array([18.0, y_goal, z_pos]),
                    'radius': 0.5
                })
        else:
            swarm_size = 5 if scenario_id == "cyber_city" else 3
            drones = _make_crossing_drones(env, n=swarm_size, radius=0.5)
        
        print(f"DEBUG: Solving {scenario_id} ({solver_type})...")
        trajectories = active_manager.solve_swarm(drones, solver_type=solver_type)
        labeled_trajectories = [{"solver": solver_type, "path": np.asarray(t).tolist()} for t in trajectories]
        
        # Add the control points for consistent markers (handles all scenarios)
        control_points = [{"start": d['start'].tolist(), "goal": d['goal'].tolist()} for d in drones]
        
    # Default fallback for control_points if none were created (e.g. torture_track)
    if 'control_points' not in locals():
        control_points = []

    print(f"DEBUG: Trajectories Count: {len(labeled_trajectories)}")

    payload = {
        "scenario": scenario_id,
        "solver": solver_type,
        "bounds": [list(env.bounds[0]), list(env.bounds[1])],
        "obstacles": serialize_environment(env),
        "trajectories": labeled_trajectories,
        "control_points": control_points,
        "dynamic_T": dynamic_T,
    }
    
    # Save the full payload for lightning-fast loads on subsequent requests
    with open(cache_file, 'w') as f:
        json.dump(payload, f)
        
    _scenario_cache[cache_key] = payload
    return payload


@app.post("/kkt_query")
def kkt_query(query: KKTQuery):
    if active_manager is None:
        return {"error": "No active scenario loaded."}
    hyperplanes = active_manager.query_kkt_hyperplanes(query.point, t=query.t)
    return {"hyperplanes": hyperplanes}

# Mount the frontend folder to serve index.html and JS files directly.
# This MUST be at the bottom so it doesn't override API routes.
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    # Pass the app as an import string path to allow the file watcher to instantiate workers cleanly
    uvicorn.run("src.engine.server:app", host="127.0.0.1", port=8000, reload=True)
