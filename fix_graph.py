import matplotlib.pyplot as plt

k_values = [0, 2, 4, 6, 8]
results = {
    'APF': [0, 100, 100, 100, 100],
    'SA': [0, 0, 0, 0, 0],
    'SCP': [0, 0, 0, 0, 0]
}
colors = {'APF': 'red', 'SA': 'orange', 'SCP': 'blue'}

plt.figure(figsize=(8, 6))

for algo in ['APF', 'SA', 'SCP']:
    # Make SCP dashed and SA slightly thicker so overlapping 0% results are both visible
    line_style = '--' if algo == 'SCP' else '-'
    line_width = 3 if algo == 'SA' else 2
    
    plt.plot(k_values, results[algo], marker='o', linestyle=line_style, linewidth=line_width,
             color=colors[algo], label=algo)

plt.title('Phase 1: Collision / Failure Rate vs. Environmental Complexity')
plt.xlabel('Number of Static CSG Obstacles ($k$)')
plt.ylabel('Failure Rate (%)')
plt.ylim(-5, 105)
plt.legend()
plt.grid(True, linestyle=':', alpha=0.7)

save_path = "stress_phase1_failure_rate_fixed.png"
plt.savefig(save_path, dpi=300, bbox_inches='tight')
print(f"Fixed chart instantly generated: {save_path}")