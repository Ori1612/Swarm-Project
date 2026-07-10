# Project Summary — Guy's Part (Visualization + Benchmarking)

This document records **what was done**, **what was tested**, and **what still
needs to be done**. It covers the "Guy" side of the swarm project (the 3D
dashboard + the benchmarking suite) that runs on top of Ori's `ori/` solvers.

---

## 1. What was done

### Starting point
You uploaded ~20 trial-and-error files (multiple versions of the same modules)
plus the current project and the four guides. The task was to pick the best
version of each file, fix the bugs, and make the project produce the outputs the
guides describe.

### Which version of each duplicate was kept
| Module | Kept | Why the others were dropped |
|---|---|---|
| `guy/environments.py` | clean version | the other had stray `[cite: …]` markers that are invalid Python |
| `gap_test.py` | None-check version, then fixed | the multiprocessing variant killed CBS before it could report node counts |
| `stress_test.py` | version calling `run_swarm_scaling_benchmark` | the earlier one reused `run_stress_test` and clashed with the Phase-1 signature |
| `DroneEntity.js` | latest (comet trail + throttled rebuild) | earlier ones had no trail / rebuilt the tube every frame |
| `EnvironmentBuilder.js` | base + quaternion HalfSphere patch | the base HalfSphere ignored the plane normal orientation |
| `benchmarks.py` snippets | merged all into one file | they were partial fragments meant to be combined |

### Files delivered
**New**
- `guy/environments.py` — single source of truth for all 8 environments (exact coords from the Environment guide).
- `guy/server.py` — FastAPI backend: `GET /scenario/{id}`, `POST /kkt_query`, health check.
- `frontend/` — modular Three.js dashboard: `index.html`, `main.js`, `SceneManager.js`, `EnvironmentBuilder.js`, `DroneEntity.js`, `UIManager.js`.
- `requirements.txt`, `README.md`.

**Updated / rewritten**
- `guy/benchmarks.py` — headless Agg backend, plus the gap-test and dual-axis stress-test analytics.
- `gap_test.py` — full rewrite per the Gap Test guide.
- `stress_test.py` — full rewrite into Phase 1 + Phase 2.
- `ori/cbs_solver.py` — one performance change (see below); multi-drone behaviour unchanged.

**Unchanged** — `guy/swarm_adapter.py`, `guy/renderer.py`, and all of `ori/` except `cbs_solver.py`.

### Bugs fixed
1. **Gap-test start/goal was inside a sealed pocket.** The old `[2,2]` corner is
   walled off on two sides by the full-height L-walls, so no path exists and CBS
   searched forever. Moved start/goal to open airspace on opposite sides of the L.
2. **Wrong "memory wall" metric.** The old code parsed CBS's *high-level* node
   count, which is always 1 for a single drone. Now it reads the true *low-level*
   A\* expansions.
3. **CBS A\* never terminated.** The 4D time-expanded search (with a "wait" move)
   revisited every cell at every timestep. Added spatial-cell pruning that only
   activates when there are no drone-to-drone constraints — fast for the
   single-drone gap test, identical behaviour for multi-drone CBS. Also added
   `stats` (node counting) and `max_nodes` (RAM safeguard) hooks.
4. **`server.py` crash.** `export_swarm_to_json("")` raised `FileNotFoundError`;
   now trajectories are serialized inline. Drone start/goals are scaled to each
   environment's bounds (so Cyber-City drones cross the full 100³ space).
5. **Blocking plots.** `benchmarks.py` now uses `matplotlib.use('Agg')` and
   `plt.savefig(..., bbox_inches='tight')` everywhere — no `plt.show()`.
6. **`ori/obstacles` import.** The package `__init__` is empty, so the primitives
   are imported from their submodules.
7. **Speed.** SCP (SLSQP) cost explodes with T, so the benchmarks use T=30 and the
   dashboard defaults the tight scenarios to the fast SA solver (`?solver=SCP`
   forces the geodesic).

---

## 2. What was tested (and the results)

All tests were run in a Linux sandbox with numpy/scipy/matplotlib/fastapi.

| Test | Result |
|---|---|
| `python -m guy.environments` | All 8 configs build with the exact obstacle counts (15 / 3 / 0,2,4,6,8 / 4). |
| `gap_test.py` (dx = 2.0, 1.0, 0.5)* | SCP flat at **23.47 m**; CBS **26.14 → 25.56 → 25.56** (asymptotes, never crosses); A\* nodes **80 → 516 → 3804** (~cubic); gap **8.9%**. Both PNGs written. |
| `stress_test.py` (reduced scope)** | Phase 1: APF failure **0% → 100%**, SA **0% → 0%** (matches expected trend). Phase 2: SA runtime recorded. Both PNGs written. |
| FastAPI backend (TestClient) | `GET /` OK; `cyber_city` → APF, 15 obstacles, 3 drones, T=30, bounds [0,100]³; `torture_track` 2.4 s, `csg_maze` 3.3 s; `POST /kkt_query` returns a hyperplane; invalid id handled gracefully. |
| Frontend JS | All 5 modules pass `node --check` (syntax valid). |
| `py_compile` | Every `.py` in `guy/`, `ori/`, and the top-level scripts compiles. |

\* dx = 0.2 was skipped in the sandbox only for time (it builds a ~1M-cell grid).
\*\* Reduced to APF+SA, k = {0,2}, N = {2}, trials = 1 to fit the sandbox time budget.

---

## 3. What still needs to be done (on your machine)

- [ ] **Run the full gap test**, including dx = 0.2. That step is intentionally
      heavy (~1–2 min, the "memory wall") and is capped so it can't crash.
- [ ] **Run the full stress test** (all k = {0,2,4,6,8}, all N = {2,4,6,8,10},
      with SCP included). This takes several minutes because SCP is slow. Confirm
      Phase 1 shows SCP staying near 0% and Phase 2 shows SA curving up vs SCP flat.
      If it's too slow, lower `trials` or `T_HORIZON` at the top of `stress_test.py`.
- [ ] **Open the dashboard in a real browser.** WebGL/Three.js can't be run in the
      sandbox — only syntax was checked. Start the backend (`python -m guy.server`)
      and a static server in `frontend/` (`python -m http.server 5500`), then open
      the page and verify: obstacles render as glowing wireframes, the time slider
      scrubs smoothly, the three camera modes work, scenario hot-swap works, and
      Math Mode draws a KKT plane when you click a drone.
- [ ] **(Optional) Sanity-check Phase-1 drone starts at k=8.** The two vertical
      pillars sit at x≈3 and x≈17, y=10; a couple of the fixed drone starts pass
      close to them. If SA/SCP show unexpected failures at k=8, nudge those
      start/goal y-values a little.
- [ ] **(Optional) Decide the viewer's default solver.** Tight scenarios currently
      default to SA for responsiveness; switch the map in `guy/server.py`
      (`SCENARIO_SOLVER`) back to `SCP` if you prefer the geodesic and don't mind
      the wait.
- [ ] **Confirm it drops into your latest `ori/`.** These files were built against
      the `ori/` package in the zip you sent. Only `ori/cbs_solver.py` was touched.

---

## 4. How to run (quick reference — full details in README.md)

```
pip install -r requirements.txt

# benchmarks (save PNGs, no window)
python gap_test.py
python stress_test.py

# dashboard
python -m guy.server                 # terminal 1  -> http://127.0.0.1:8000
cd frontend && python -m http.server 5500   # terminal 2 -> open http://localhost:5500
```
