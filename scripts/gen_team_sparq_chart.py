#!/usr/bin/env python3
"""
Generate team SPARQ draft grade chart for the 2026 draft.
Horizontal bar chart, all 32 teams ranked by average z-score.
"""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

sys.path.insert(0, os.path.dirname(__file__))
from scrape import _norm_name

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
OUT_DIR  = os.path.join(os.path.dirname(__file__), '..', 'blogs', 'sparq-draft-grades-2026')

BG      = '#0d0f1a'
TEXT_C  = '#8899bb'
LABEL_C = '#c8d4f0'
GRID_C  = '#1a1e30'

# Tier definitions and colors
TIERS = [
    ('Built Different', 1.0,   '#4a7fd4'),  # z >= 1.0
    ('On Trend',        0.7,   '#3a9e6e'),  # 0.7 <= z < 1.0
    ('Film-First',      0.4,   '#c8a040'),  # 0.4 <= z < 0.7
    ('Gambling on Skill', -99, '#c04a4a'),  # z < 0.4
]

def tier_color(z):
    for label, threshold, color in TIERS:
        if z >= threshold:
            return color, label
    return '#c04a4a', 'Gambling on Skill'

# ── Load 2026 prospects ───────────────────────────────────────────────────────
prospects = json.load(open(os.path.join(DATA_DIR, 'prospects_2026.json')))['prospects']

from collections import defaultdict
team_scores = defaultdict(list)
team_nulls  = defaultdict(int)

for p in prospects:
    if p.get('round_source') != 'actual':
        continue
    team = p.get('team')
    if not team:
        continue
    z = p.get('z_score')
    if z is not None:
        team_scores[team].append(z)
    else:
        team_nulls[team] += 1

# Compute averages, require at least 2 scored picks
team_avgs = {}
for team, scores in team_scores.items():
    if len(scores) >= 2:
        team_avgs[team] = (sum(scores) / len(scores), len(scores), team_nulls[team])

# Sort descending
ranked = sorted(team_avgs.items(), key=lambda x: x[1][0], reverse=True)

print(f"Teams with data: {len(ranked)}")
for team, (avg, n, nulls) in ranked:
    color, tier = tier_color(avg)
    print(f"  {team:4} {avg:+.3f}  n={n}  nulls={nulls}  [{tier}]")

# ── Chart: horizontal bar ─────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 13), facecolor=BG)
ax.set_facecolor(BG)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_color(GRID_C)
ax.tick_params(colors=TEXT_C, labelsize=9.5)
ax.xaxis.grid(True, color=GRID_C, linewidth=0.6, zorder=0)
ax.set_axisbelow(True)

teams  = [t for t, _ in ranked]
avgs   = [v[0] for _, v in ranked]
ns     = [v[1] for _, v in ranked]
colors = [tier_color(z)[0] for z in avgs]

y = np.arange(len(teams))
bars = ax.barh(y, avgs, 0.65, color=colors, alpha=0.88, zorder=3)

# Zero line
ax.axvline(0, color='#2a2e40', linewidth=1.2, zorder=2)

# Value labels
for i, (avg, n) in enumerate(zip(avgs, ns)):
    x_pos = avg + 0.03 if avg >= 0 else avg - 0.03
    ha = 'left' if avg >= 0 else 'right'
    ax.text(x_pos, i, f'{avg:+.2f}', ha=ha, va='center',
            fontsize=8.5, color=LABEL_C, fontweight='600',
            fontfamily='monospace')

# n= labels on left side
for i, n in enumerate(ns):
    ax.text(-1.35, i, f'n={n}', ha='left', va='center',
            fontsize=7.5, color=TEXT_C, fontfamily='monospace')

ax.set_yticks(y)
ax.set_yticklabels(teams, color=LABEL_C, fontsize=10.5, fontweight='600')
ax.set_xlim(-1.5, 2.2)
ax.set_ylim(-0.6, len(teams) - 0.4)
ax.invert_yaxis()
ax.set_xlabel('Average SPARQ z-score (drafted players with combine data)', color=TEXT_C, fontsize=9.5, labelpad=10)

# Tier background bands
tier_boundaries = [(1.0, 2.2, '#4a7fd4'), (0.7, 1.0, '#3a9e6e'),
                   (0.4, 0.7, '#c8a040'), (-1.5, 0.4, '#c04a4a')]
for xmin, xmax, color in tier_boundaries:
    ax.axvspan(xmin, xmax, alpha=0.04, color=color, zorder=0)

# Legend
patches = [mpatches.Patch(color=c, label=l, alpha=0.88)
           for l, _, c in TIERS]
ax.legend(handles=patches, frameon=False, labelcolor=LABEL_C, fontsize=9,
          loc='lower right', handlelength=1.0, handleheight=0.9)

ax.set_title('2026 NFL Draft — Team SPARQ Grades\nAverage z-score of drafted players with combine data',
             color=LABEL_C, fontsize=11, pad=14, loc='left', linespacing=1.6)

fig.tight_layout(pad=1.6)
out = os.path.join(OUT_DIR, 'team-sparq-grades.png')
fig.savefig(out, dpi=160, facecolor=BG, bbox_inches='tight')
plt.close(fig)
print(f'\nSaved: {out}')
