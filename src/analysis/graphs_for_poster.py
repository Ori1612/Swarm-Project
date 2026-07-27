import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# Set global font and style defaults
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['axes.edgecolor'] = '#000000'
plt.rcParams['axes.linewidth'] = 1.0

# Data extracted precisely from the results table
resolution = [2.0, 1.0, 0.5, 0.25]
cbs_length = [25.76, 25.76, 24.83, 24.41]
scp_length = [22.41, 22.41, 22.41, 22.41]
nodes_expanded = [86, 625, 4662, 68657]

# -------------------------------------------------------------
# FIGURE 1: Path Length vs Resolution (Square Mode)
# -------------------------------------------------------------
fig1, ax1 = plt.subplots(figsize=(6.0, 6.0), dpi=300)

ax1.set_axisbelow(True)

ax1.plot(
    resolution,
    cbs_length,
    color='#2980B9',
    marker='s',
    linestyle='-',
    linewidth=2.5,
    markersize=8,
    label='CBS (Discrete)',
)
ax1.plot(
    resolution,
    scp_length,
    color='#5C4EA2',
    marker='s',
    linestyle='-',
    linewidth=2.5,
    markersize=8,
    label='SCP (Convex)',
)

# Invert X-axis, set limits, and use 0.5 resolution jumps
ax1.set_xlim(2.2, 0.1)
ax1.set_xticks([2.0, 1.5, 1.0, 0.5])

# Major gridlines only with exact requested color
ax1.grid(True, which='major', color='#C9DAF8', linestyle='-', linewidth=0.8)
ax1.grid(False, which='minor')

# Ensure bold axis tick numbers
ax1.tick_params(axis='both', which='major', labelsize=10, colors='#000000')
for label in ax1.get_xticklabels() + ax1.get_yticklabels():
  label.set_fontweight('bold')
  label.set_color('#000000')

ax1.set_xlabel(
    r'Grid Resolution $\Delta x$ (m)',
    fontsize=11,
    fontweight='bold',
    color='#000000',
)
ax1.set_ylabel('')

ax1.set_title(
    r'Figure 1: Total Path Length (m)'
    + '\n'
    + r'vs. Grid Resolution $\Delta x$ (m)',
    fontsize=10.5,
    fontweight='bold',
    pad=10,
    color='#000000',
)

ax1.legend(
    frameon=True,
    facecolor='#F8F9F9',
    edgecolor='#000000',
    fontsize=9.5,
    loc='upper right',
)
fig1.tight_layout(rect=[0, 0, 1, 0.96])
fig1.savefig('figure1_path_length.png', dpi=300)
plt.close(fig1)

# -------------------------------------------------------------
# FIGURE 2: A* Nodes Expanded (Log Scale) vs Resolution (Square Mode)
# -------------------------------------------------------------
fig2, ax2 = plt.subplots(figsize=(6.0, 6.0), dpi=300)

ax2.set_axisbelow(True)

ax2.plot(
    resolution,
    nodes_expanded,
    color='#A64D79',
    marker='s',
    linestyle='-',
    linewidth=2.5,
    markersize=8,
)

ax2.set_yscale('log')
ax2.set_xlim(2.2, 0.1)
ax2.set_xticks([2.0, 1.5, 1.0, 0.5])

# Major gridlines only
ax2.grid(True, which='major', color='#C9DAF8', linestyle='-', linewidth=0.8)
ax2.grid(False, which='minor')

# Format Y-axis log scale ticks as bold 10^x powers using \mathbf{}
ax2.yaxis.set_major_locator(ticker.LogLocator(base=10.0, numticks=6))
ax2.yaxis.set_major_formatter(
    ticker.FuncFormatter(
        lambda y, _: f'$\\mathbf{{10^{int(np.log10(y))}}}$'
    )
)

# Ensure bold axis tick numbers explicitly for ticks
ax2.tick_params(axis='both', which='major', labelsize=10, colors='#000000')
for label in ax2.get_xticklabels() + ax2.get_yticklabels():
  label.set_fontweight('bold')
  label.set_color('#000000')

ax2.set_xlabel(
    r'Grid Resolution $\Delta x$ (m)',
    fontsize=11,
    fontweight='bold',
    color='#000000',
)
ax2.set_ylabel('')

ax2.set_title(
    r'Figure 2: A* Nodes Expanded (Log Scale)'
    + '\n'
    + r'vs. Grid Resolution $\Delta x$ (m)',
    fontsize=10.5,
    fontweight='bold',
    pad=10,
    color='#000000',
)

fig2.tight_layout(rect=[0, 0, 1, 0.96])
fig2.savefig('figure2_nodes_expanded.png', dpi=300)
plt.close(fig2)