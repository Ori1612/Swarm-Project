# Swarm Path-Planning — Guy's Modules (Visualization + Benchmarking)

This is the "Guy" side of the project: the interactive 3D dashboard and the
benchmarking suite, built on top of Ori's `ori/` solver package. It implements
the four guides (Environment Configurations, Gap Test, Stress Test, Visualization).

## What's here

```
final_project_code/
├── guy/
│   ├── environments.py   NEW  – single source of truth for all 8 environments
│   ├── server.py         NEW  – FastAPI backend (scenario + KKT endpoints)
│   ├── benchmarks.py     UPDATED – headless (Agg) plots + gap/stress analytics
│   ├── swarm_adapter.py       – (unchanged) collision check + solver callbacks
│   └── renderer.py            – (unchanged) legacy matplotlib viewer
├── frontend/             NEW  – modular Three.js dashboard
│   ├── index.html
│   ├── main.js                – orchestrator
│   ├── SceneManager.js        – renderer / camera / lights
│   ├── EnvironmentBuilder.js  – glowing CSG wireframes + KKT planes
│   ├── DroneEntity.js         – lerp interpolation + comet trails
│   └── UIManager.js           – controls, camera modes, Math Mode raycast
├── gap_test.py           REWRITTEN – sub-optimality gap test (CBS vs SCP)
├── stress_test.py        REWRITTEN – dual-axis stress test (Phase 1 + Phase 2)
├── ori/                       – Ori's solvers (see note on cbs_solver.py below)
└── requirements.txt
```

## Install

```
pip install -r requirements.txt
```

## Run the benchmarks (headless — they save PNGs, no window pops up)

```
python gap_test.py       # -> gap_test_resolution_vs_pathlength.png
                         #    gap_test_resolution_vs_nodes_expanded.png
python stress_test.py    # -> stress_phase1_failure_rate.png
                         #    stress_phase2_runtime.png
```

Expected results:
* Gap test: SCP is a flat geodesic line; CBS starts longer and asymptotes toward
  it (never crossing). CBS A* nodes-expanded explodes ~cubically as Δx shrinks.
* Stress Phase 1: APF failure rate spikes toward 100% as obstacles are added,
  while SA/SCP stay near 0%. Phase 2: SA runtime curves up, SCP scales flatter.

Note: `gap_test.py` includes Δx = 0.2. That grid is ~1M cells and is deliberately
heavy (the "memory wall"); expect that single step to take a minute or two.

## Run the interactive 3D dashboard

Two terminals from the project root:

```
# 1) backend  (http://127.0.0.1:8000)
python -m guy.server

# 2) frontend (any static server; must be http, not file://)
cd frontend
python -m http.server 5500
```

Then open http://localhost:5500 . Use the dropdown to hot-swap scenarios, the
slider to scrub time, the camera buttons, and Math Mode (click a drone to project
its KKT tangent plane). Add `?solver=SCP` server-side to force the slower
continuous geodesic on any scenario.

## Key fixes made to the trial-and-error files
* `guy/environments.py` — removed the stray `[cite: …]` markers that broke the
  file; import the CSG primitives from their submodules (the package `__init__`
  is empty).
* `gap_test.py` — start/goal moved into open airspace on opposite sides of the
  L-trap (the old `[2,2]` corner is sealed off by the full-height walls, so no
  path existed); reads the true low-level A* node count; runs SCP once.
* `stress_test.py` — uses the renamed `run_swarm_scaling_benchmark` for Phase 2
  so it no longer clashes with the Phase-1 signature.
* `guy/server.py` — fixed the `export_swarm_to_json("")` crash (serialized inline);
  scaled drone start/goals to each environment's bounds.
* `guy/benchmarks.py` — Agg backend + `plt.savefig(..., bbox_inches='tight')`
  everywhere (no more blocking `plt.show()`).
* `ori/cbs_solver.py` — one performance change (see below).

## Note on `ori/cbs_solver.py`
The 4D A* is time-expanded with a "wait" move (needed for multi-drone conflicts).
For a single unconstrained drone that made it revisit every cell at every timestep
and effectively never finish. Added: (a) spatial-cell pruning that activates only
when no time-specific constraints are present — collapsing the search to a fast 3D
A* for the single-drone gap test while leaving multi-drone CBS behaviour intact;
(b) optional `stats`/`max_nodes` hooks so the gap test can read node counts and cap
runaway searches. Multi-drone CBS results are unchanged.
