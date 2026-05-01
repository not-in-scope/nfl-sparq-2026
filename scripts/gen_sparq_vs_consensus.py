#!/usr/bin/env python3
"""
Scatter plot: SPARQ z-score vs consensus draft grade.
Shows where athleticism and scout opinion align or diverge.
"""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
OUT_DIR  = os.path.join(os.path.dirname(__file__), '..', 'blogs', 'sparq-draft-grades-2026')

BG      = '#0d0f1a'
TEXT_C  = '#8899bb'
LABEL_C = '#c8d4f0'
GRID_C  = '#1a1e30'

# Grade -> numeric
GRADE_MAP = {
    'A+': 4.3, 'A': 4.0, 'A-': 3.7,
    'B+': 3.3, 'B': 3.0, 'B-': 2.7,
    'C+': 2.3, 'C': 2.0, 'C-': 1.7,
    'D+': 1.3, 'D': 1.0, 'D-': 0.7,
}

# Consensus grades from ESPN, NFL.com, PFF, CBS Sports
CONSENSUS = {
    'ARI': {'ESPN': 'B',  'NFL.com': 'B',  'PFF': 'C+', 'CBS': 'B+'},
    'ATL': {              'NFL.com': 'C+', 'PFF': 'C+', 'CBS': 'C' },
    'BAL': {'ESPN': 'B+', 'NFL.com': 'A-', 'PFF': 'B+', 'CBS': 'C+'},
    'BUF': {              'NFL.com': 'C',  'PFF': 'B',  'CBS': 'B-'},
    'CAR': {'ESPN': 'B',  'NFL.com': 'B+', 'PFF': 'A+', 'CBS': 'C' },
    'CHI': {'ESPN': 'B',  'NFL.com': 'B+', 'PFF': 'B',  'CBS': 'B-'},
    'CIN': {'ESPN': 'B',  'NFL.com': 'B',  'PFF': 'B+', 'CBS': 'B-'},
    'CLE': {'ESPN': 'A',  'NFL.com': 'A',  'PFF': 'A+', 'CBS': 'B+'},
    'DAL': {'ESPN': 'A',  'NFL.com': 'A-', 'PFF': 'B',  'CBS': 'A' },
    'DEN': {              'NFL.com': 'C+', 'PFF': 'C-', 'CBS': 'C+'},
    'DET': {'ESPN': 'B',  'NFL.com': 'B',  'PFF': 'B-', 'CBS': 'C' },
    'GB':  {              'NFL.com': 'C+', 'PFF': 'B',  'CBS': 'B-'},
    'HOU': {              'NFL.com': 'B-', 'PFF': 'B-', 'CBS': 'B' },
    'IND': {'ESPN': 'B+', 'NFL.com': 'B',  'PFF': 'A',  'CBS': 'B-'},
    'JAX': {                               'PFF': 'D+', 'CBS': 'C+'},
    'KC':  {'ESPN': 'B',  'NFL.com': 'A-', 'PFF': 'B',  'CBS': 'A+'},
    'LV':  {'ESPN': 'A',  'NFL.com': 'A-', 'PFF': 'A-', 'CBS': 'B+'},
    'LAC': {'ESPN': 'B',  'NFL.com': 'B+', 'PFF': 'B',  'CBS': 'B+'},
    'LAR': {                               'PFF': 'C'               },
    'MIA': {'ESPN': 'B',  'NFL.com': 'A-', 'PFF': 'B+'             },
    'MIN': {              'NFL.com': 'B-', 'PFF': 'C'               },
    'NE':  {              'NFL.com': 'C+', 'PFF': 'C+'              },
    'NO':  {              'NFL.com': 'B',  'PFF': 'B'               },
    'NYG': {'ESPN': 'B+', 'NFL.com': 'A',  'PFF': 'A',  'CBS': 'A' },
    'NYJ': {'ESPN': 'A-', 'NFL.com': 'A-', 'PFF': 'A-', 'CBS': 'A+'},
    'PHI': {'ESPN': 'A',  'NFL.com': 'B+', 'PFF': 'B+'             },
    'PIT': {              'NFL.com': 'B-', 'PFF': 'C+'              },
    'SF':  {                               'PFF': 'D'               },
    'SEA': {              'NFL.com': 'C',  'PFF': 'C-', 'CBS': 'A' },
    'TB':  {              'NFL.com': 'A-', 'PFF': 'B+'              },
    'TEN': {              'NFL.com': 'B',                'CBS': 'A' },
    'WSH': {              'NFL.com': 'B-'                            },
}

def avg_grade(grades):
    nums = [GRADE_MAP[g] for g in grades.values() if g in GRADE_MAP]
    return sum(nums) / len(nums) if nums else None

# Load SPARQ team averages
prospects = json.load(open(os.path.join(DATA_DIR, 'prospects_2026.json')))['prospects']
team_scores = defaultdict(list)
for p in prospects:
    if p.get('round_source') != 'actual': continue
    team = p.get('team')
    z    = p.get('z_score')
    if team and z is not None:
        team_scores[team].append(z)
team_avgs = {t: sum(s)/len(s) for t, s in team_scores.items() if len(s) >= 2}

# Build combined dataset
data = []
for team, sparq in team_avgs.items():
    if team not in CONSENSUS: continue
    cons = avg_grade(CONSENSUS[team])
    if cons is None: continue
    n_grades = len([g for g in CONSENSUS[team].values() if g in GRADE_MAP])
    data.append((team, sparq, cons, n_grades))

data.sort(key=lambda x: x[1])

# Quadrant labels
teams       = [d[0] for d in data]
sparq_vals  = np.array([d[1] for d in data])
cons_vals   = np.array([d[2] for d in data])
sparq_med   = np.median(sparq_vals)
cons_med    = np.median(cons_vals)

# Color by quadrant
def quad_color(sparq, cons):
    high_s = sparq >= sparq_med
    high_c = cons  >= cons_med
    if high_s and high_c:  return '#4a7fd4'   # both high — blue
    if high_s and not high_c: return '#c8a040' # high SPARQ, low consensus — amber
    if not high_s and high_c: return '#c04a4a' # low SPARQ, high consensus — red
    return '#556688'                            # both low — muted

colors = [quad_color(s, c) for s, c in zip(sparq_vals, cons_vals)]

# ── Figure ─────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(11, 7), facecolor=BG)
ax.set_facecolor(BG)
ax.spines['bottom'].set_color(GRID_C)
ax.spines['left'].set_color(GRID_C)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.tick_params(colors=TEXT_C, labelsize=9.5)
ax.yaxis.grid(True, color=GRID_C, linewidth=0.5, zorder=0)
ax.xaxis.grid(True, color=GRID_C, linewidth=0.5, zorder=0)
ax.set_axisbelow(True)

# Quadrant dividers
ax.axvline(sparq_med, color='#2a2e40', linewidth=1, linestyle='--', zorder=1)
ax.axhline(cons_med,  color='#2a2e40', linewidth=1, linestyle='--', zorder=1)

# Quadrant labels (faint)
ax.text(sparq_med - 0.04, cons_med + 0.05, 'Low SPARQ\nHigh consensus',
        ha='right', va='bottom', fontsize=8, color='#c04a4a', alpha=0.5,
        style='italic')
ax.text(sparq_med + 0.04, cons_med + 0.05, 'High SPARQ\nHigh consensus',
        ha='left', va='bottom', fontsize=8, color='#4a7fd4', alpha=0.5,
        style='italic')
ax.text(sparq_med - 0.04, cons_med - 0.05, 'Low SPARQ\nLow consensus',
        ha='right', va='top', fontsize=8, color='#556688', alpha=0.5,
        style='italic')
ax.text(sparq_med + 0.04, cons_med - 0.05, 'High SPARQ\nLow consensus',
        ha='left', va='top', fontsize=8, color='#c8a040', alpha=0.5,
        style='italic')

# Scatter
ax.scatter(sparq_vals, cons_vals, c=colors, s=60, zorder=4, alpha=0.9)

# Labels — offset to avoid overlap
offsets = {
    'KC':  (0.04,  0.04), 'NYG': (0.04,  0.04), 'SEA': (0.04, -0.06),
    'CAR': (-0.04, 0.04), 'NO':  (0.04, -0.06), 'SF':  (0.04, -0.06),
    'JAX': (0.04,  0.04), 'CLE': (0.04, -0.06), 'NYJ': (-0.04, 0.04),
    'DAL': (0.04,  0.04), 'LV':  (-0.04, 0.04), 'PHI': (0.04, -0.06),
}
for team, sparq, cons, _ in data:
    dx, dy = offsets.get(team, (0.04, 0.04))
    ax.text(sparq + dx, cons + dy, team,
            ha='left' if dx > 0 else 'right', va='center',
            fontsize=8.5, color=LABEL_C, fontweight='600',
            fontfamily='monospace', zorder=5)

# Grade labels on y-axis
grade_ticks = [(4.3,'A+'), (4.0,'A'), (3.7,'A-'), (3.3,'B+'), (3.0,'B'),
               (2.7,'B-'), (2.3,'C+'), (2.0,'C'), (1.7,'C-')]
ax.set_yticks([g[0] for g in grade_ticks])
ax.set_yticklabels([g[1] for g in grade_ticks], color=TEXT_C,
                   fontfamily='monospace', fontsize=9.5)
ax.set_xlabel('SPARQ z-score (avg of drafted players with combine data)',
              color=TEXT_C, fontsize=10, labelpad=10)
ax.set_ylabel('Consensus draft grade\n(avg of ESPN, NFL.com, PFF, CBS Sports)',
              color=TEXT_C, fontsize=10, labelpad=10)
ax.set_title('SPARQ athleticism vs. consensus draft grade   (2026 NFL Draft)',
             color=LABEL_C, fontsize=11, pad=14, loc='left')

fig.tight_layout(pad=1.6)
out = os.path.join(OUT_DIR, 'sparq-vs-consensus.png')
fig.savefig(out, dpi=160, facecolor=BG, bbox_inches='tight')
plt.close(fig)
print(f'Saved: {out}')

# Print biggest divergences
print('\n--- Biggest divergences ---')
diffs = [(t, s, c, s - (c - 2.0) * 0.5) for t, s, c, _ in data]
print('High SPARQ, low consensus (underrated athletically by scouts):')
for team, sparq, cons, _ in sorted(data, key=lambda x: x[1]-x[2]*0.3, reverse=True)[:5]:
    print(f'  {team}: SPARQ={sparq:+.2f}, consensus={cons:.2f}')
print('Low SPARQ, high consensus (scouts loved but tested poorly):')
for team, sparq, cons, _ in sorted(data, key=lambda x: x[2]-x[1]*0.5, reverse=True)[:5]:
    print(f'  {team}: SPARQ={sparq:+.2f}, consensus={cons:.2f}')
