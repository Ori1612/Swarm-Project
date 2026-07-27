from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import numpy as np

# Set global font and style defaults
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['axes.edgecolor'] = '#000000'
plt.rcParams['axes.linewidth'] = 1.0

# -------------------------------------------------------------
# FIGURE 3: Phase 1 - Failure Rate vs. Obstacles (Square Layout)
# -------------------------------------------------------------
fig3, ax3 = plt.subplots(figsize=(6.0, 6.0), dpi=300)

k_obs = np.array([0, 2, 4, 6, 8])
apf_fail = np.array([100, 100, 100, 100, 100])
sa_fail = np.array([0, 0, 0, 0, 0])
scp_fail = np.array([0, 0, 0, 0, 0])

# Ensure grid lines are strictly rendered below all plot elements
ax3.set_axisbelow(True)

# APF: color #A64D79, pentagon marker 'p', continuous line, high zorder to sit above grid
ax3.plot(
    k_obs,
    apf_fail,
    marker='p',
    markersize=9,
    color='#A64D79',
    linewidth=2.2,
    linestyle='-',
    zorder=3,
)

# SCP: square marker 's' (size 11), line width 3.0, continuous line
ax3.plot(
    k_obs,
    scp_fail,
    marker='s',
    markersize=11,
    color='#46BDC6',
    linewidth=3.0,
    linestyle='-',
    zorder=2,
)

# SA: circle marker 'o' (size 9), line width 3.0, discontinuous dashes ([5, 6]), layered on top
ax3.plot(
    k_obs,
    sa_fail,
    marker='o',
    markersize=9,
    color='#3D85C6',
    linewidth=3.0,
    dashes=[5, 6],
    zorder=4,
)

ax3.set_xlim(-0.2, 8.5)
ax3.set_ylim(-5, 108)

# X-axis label only (no vertical axis title text)
ax3.set_xlabel(
    r'Number of Static CSG Obstacles ($k$)',
    fontsize=11,
    fontweight='bold',
    color='#000000',
)
ax3.set_ylabel('')

# Two-line title to prevent truncation
ax3.set_title(
    r'Figure 3: Phase 1 — Failure Rate (%)'
    + '\n'
    + r'vs. Environmental Complexity ($k$)',
    fontsize=10.5,
    fontweight='bold',
    pad=10,
    color='#000000',
)

# Major grid lines with color #C9DAF8
ax3.grid(True, color='#C9DAF8', linestyle='-', linewidth=0.8)
ax3.set_facecolor('#FFFFFF')
fig3.patch.set_facecolor('#FFFFFF')

# Make all tick numbers bold and black
for tick in ax3.get_xticklabels():
  tick.set_weight('bold')
  tick.set_color('#000000')
for tick in ax3.get_yticklabels():
  tick.set_weight('bold')
  tick.set_color('#000000')

# Use proxy handles for the legend to keep SCP's legend marker standard size
apf_legend = Line2D(
    [0],
    [0],
    marker='p',
    color='#A64D79',
    markersize=6,
    linewidth=2.2,
    linestyle='-',
    label='APF (Reactive)',
)
scp_legend = Line2D(
    [0],
    [0],
    marker='s',
    color='#46BDC6',
    markersize=6,
    linewidth=3.0,
    linestyle='-',
    label='SCP (Convex)',
)
sa_legend = Line2D(
    [0],
    [0],
    marker='o',
    color='#3D85C6',
    markersize=6,
    linewidth=3.0,
    dashes=[5, 6],
    label='SA (Stochastic)',
)

ax3.legend(
    handles=[apf_legend, scp_legend, sa_legend],
    frameon=True,
    facecolor='#F8F9F9',
    edgecolor='#000000',
    fontsize=9.5,
    loc='center right',
)
plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig('figure3_phase1_failure_rate.png', dpi=300)
plt.close(fig3)

# -------------------------------------------------------------
# FIGURE 4: Phase 2 - Computational Runtime vs. Swarm Scale (Square Layout)
# -------------------------------------------------------------
fig4, ax4 = plt.subplots(figsize=(6.0, 6.0), dpi=300)

swarm_scale = np.array([2, 4, 6, 8, 10])
sa_runtime = np.array([1.2, 2.1, 3.5, 13.2, 18.0])
scp_runtime = np.array([12.5, 30.0, 88.5, 371.0, 504.2])

ax4.set_axisbelow(True)

ax4.plot(
    swarm_scale,
    sa_runtime,
    marker='s',
    color='#2980B9',
    linewidth=2.2,
    label='SA (Decoupled)',
)
ax4.plot(
    swarm_scale,
    scp_runtime,
    marker='s',
    color='#5C4EA2',
    linewidth=2.2,
    label=r'SCP (Decoupled $\mathcal{O}(N)$)',
)

ax4.set_xlim(1.5, 10.5)
ax4.set_ylim(-20, 540)

# X-axis label only (no vertical axis title text)
ax4.set_xlabel(
    r'Swarm Scale ($N$ drones)', fontsize=11, fontweight='bold', color='#000000'
)
ax4.set_ylabel('')

# Two-line title to prevent truncation
ax4.set_title(
    r'Figure 4: Phase 2 — Average Runtime (s)'
    + '\n'
    + r'vs. Swarm Scale ($N$)',
    fontsize=10.5,
    fontweight='bold',
    pad=10,
    color='#000000',
)

# Major grid lines with color #C9DAF8
ax4.grid(True, color='#C9DAF8', linestyle='-', linewidth=0.8)
ax4.set_facecolor('#FFFFFF')
fig4.patch.set_facecolor('#FFFFFF')

# Make all tick numbers bold and black
for tick in ax4.get_xticklabels():
  tick.set_weight('bold')
  tick.set_color('#000000')
for tick in ax4.get_yticklabels():
  tick.set_weight('bold')
  tick.set_color('#000000')

ax4.legend(
    frameon=True,
    facecolor='#F8F9F9',
    edgecolor='#000000',
    fontsize=9.5,
    loc='upper left',
)
plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig('figure4_phase2_runtime.png', dpi=300)
plt.close(fig4)