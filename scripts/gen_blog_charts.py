#!/usr/bin/env python3
"""Regenerate blog charts for low-sparq-nfl-success post."""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import to_rgba

sys.path.insert(0, os.path.dirname(__file__))
from scrape import _norm_name

DATA_DIR   = os.path.join(os.path.dirname(__file__), '..', 'data')
CAREER_PATH = os.path.join(DATA_DIR, 'career_seasons.json')
OUT_DIR    = os.path.join(os.path.dirname(__file__), '..', 'blogs', 'low-sparq-nfl-success')

# ── Load career data ──────────────────────────────────────────────────────────
career_raw = json.load(open(CAREER_PATH))
career = {_norm_name(k): v for k, v in career_raw.items()}

# ── Load prospects 2010-2020 ──────────────────────────────────────────────────
players = []
for year in range(2010, 2021):
    path = os.path.join(DATA_DIR, f'prospects_{year}.json')
    if not os.path.exists(path):
        continue
    d = json.load(open(path))
    for p in d['prospects']:
        if p.get('z_score') is None or not p.get('draft_round'):
            continue
        norm = _norm_name(p['name'])
        seasons = career.get(norm, [])
        n_seasons = len(seasons)
        if   n_seasons >= 8: outcome = 'Star'
        elif n_seasons >= 5: outcome = 'Solid'
        elif n_seasons >= 3: outcome = 'Serviceable'
        else:                outcome = 'Bust'
        players.append({
            'name':    p['name'],
            'z_score': p['z_score'],
            'round':   p['draft_round'],
            'outcome': outcome,
            'seasons': n_seasons,
        })

print(f'Players loaded: {len(players)}')

def sparq_tier(z):
    if   z >= 2.0:  return 'ELITE'
    elif z >= 1.0:  return 'GREAT'
    elif z >= 0.0:  return 'GOOD'
    elif z >= -1.0: return 'AVERAGE'
    elif z >= -2.0: return 'BELOW AVG'
    else:           return 'POOR'

for p in players:
    p['tier'] = sparq_tier(p['z_score'])
    if   p['round'] <= 2: p['round_grp'] = 'R1-2'
    elif p['round'] <= 5: p['round_grp'] = 'R3-5'
    else:                  p['round_grp'] = 'R6-7'

# ── Style constants ───────────────────────────────────────────────────────────
BG       = '#0d0f1a'
AX_BG    = '#0d0f1a'
GRID_C   = '#1a1e30'
TEXT_C   = '#8899bb'
LABEL_C  = '#c8d4f0'
TIERS    = ['ELITE', 'GREAT', 'GOOD', 'AVERAGE', 'BELOW AVG', 'POOR']
OUTCOMES = ['Star', 'Solid', 'Serviceable', 'Bust']

# Outcome palette — muted, dark-mode friendly
O_COLORS = {
    'Star':        '#4a7fd4',
    'Solid':       '#3a9e6e',
    'Serviceable': '#c8a040',
    'Bust':        '#c04a4a',
}

def style_ax(ax):
    ax.set_facecolor(AX_BG)
    ax.tick_params(colors=TEXT_C, labelsize=10)
    ax.spines['bottom'].set_color(GRID_C)
    ax.spines['left'].set_color(GRID_C)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, color=GRID_C, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)

# ── Chart 1: stacked bar — outcome distribution by SPARQ tier ─────────────────
from collections import defaultdict
tier_counts = defaultdict(lambda: defaultdict(int))
for p in players:
    tier_counts[p['tier']][p['outcome']] += 1

# Leave room at top for inline legend
fig, ax = plt.subplots(figsize=(10, 5.8), facecolor=BG)
style_ax(ax)

x = np.arange(len(TIERS))
bar_w = 0.58
bottoms = np.zeros(len(TIERS))
seg_mids = {}  # for label placement

for outcome in OUTCOMES:
    vals = np.array([tier_counts[t][outcome] for t in TIERS], dtype=float)
    totals = np.array([sum(tier_counts[t].values()) for t in TIERS], dtype=float)
    totals[totals == 0] = 1
    pcts = vals / totals * 100
    ax.bar(x, pcts, bar_w, bottom=bottoms,
           color=O_COLORS[outcome], zorder=3, alpha=0.90)
    seg_mids[outcome] = bottoms + pcts / 2
    # Labels inside segments (only if segment tall enough)
    for i, (pct, bot) in enumerate(zip(pcts, bottoms)):
        if pct >= 9:
            ax.text(x[i], bot + pct / 2, f'{pct:.0f}%',
                    ha='center', va='center', fontsize=8.5,
                    color='white', alpha=0.85, fontweight='600')
    bottoms += pcts

ax.set_xticks(x)
ax.set_xticklabels(TIERS, color=LABEL_C, fontsize=10.5)
ax.set_ylabel('% of players', color=TEXT_C, fontsize=10)
ax.set_ylim(0, 112)
ax.tick_params(axis='x', bottom=False)

# n= labels above bars
for i, tier in enumerate(TIERS):
    n = sum(tier_counts[tier].values())
    ax.text(x[i], 101.5, f'n={n}', ha='center', va='bottom',
            fontsize=8, color=TEXT_C)

ax.set_title('Career outcome by SPARQ tier   (2010–2020, n=2,281)',
             color=LABEL_C, fontsize=11, pad=12, loc='left')

# Legend below the chart
patches = [mpatches.Patch(color=O_COLORS[o], label=o) for o in OUTCOMES]
ax.legend(handles=patches, frameon=False, labelcolor=LABEL_C, fontsize=9.5,
          loc='upper center', bbox_to_anchor=(0.5, -0.10), ncol=4,
          handlelength=1.2, handleheight=0.9, columnspacing=1.4)

fig.tight_layout(pad=1.4)
fig.subplots_adjust(bottom=0.14)
out1 = os.path.join(OUT_DIR, 'sparq-by-round.png')
fig.savefig(out1, dpi=160, facecolor=BG, bbox_inches='tight')
plt.close(fig)
print(f'Saved: {out1}')

# ── Chart 2: grouped bar — success rate by SPARQ band × round group ──────────
# Collapse to High / Mid / Low SPARQ
def sparq_band(z):
    if   z >= 0.674:  return 'High SPARQ\n(top 25%)'
    elif z >= -0.674: return 'Mid SPARQ\n(middle 50%)'
    else:             return 'Low SPARQ\n(bottom 25%)'

for p in players:
    p['band'] = sparq_band(p['z_score'])
    p['success'] = p['outcome'] in ('Star', 'Solid')

BANDS   = ['High SPARQ\n(top 25%)', 'Mid SPARQ\n(middle 50%)', 'Low SPARQ\n(bottom 25%)']
R_GRPS  = ['R1-2', 'R3-5', 'R6-7']
R_COLORS = ['#4a7fd4', '#3a9e6e', '#c8a040']

fig, ax = plt.subplots(figsize=(9, 5), facecolor=BG)
style_ax(ax)

n_bands  = len(BANDS)
n_rgrps  = len(R_GRPS)
bar_w    = 0.22
group_w  = n_rgrps * bar_w + 0.14
x = np.arange(n_bands) * group_w

for ri, (rgrp, color) in enumerate(zip(R_GRPS, R_COLORS)):
    rates, ns = [], []
    for band in BANDS:
        subset = [p for p in players if p['band'] == band and p['round_grp'] == rgrp]
        n = len(subset)
        rate = sum(p['success'] for p in subset) / n * 100 if n else 0
        rates.append(rate)
        ns.append(n)
    offset = (ri - 1) * bar_w
    bars = ax.bar(x + offset, rates, bar_w, color=color, alpha=0.88, zorder=3,
                  label=rgrp)
    for xi, (r, n) in enumerate(zip(rates, ns)):
        if n > 5:
            ax.text(x[xi] + offset, r + 1.2, f'{r:.0f}%',
                    ha='center', va='bottom', fontsize=8.5, color=color)

ax.set_xticks(x)
ax.set_xticklabels(BANDS, color=LABEL_C, fontsize=10.5)
ax.set_ylabel('Success rate  (5+ seasons)', color=TEXT_C, fontsize=10)
ax.set_ylim(0, 102)
ax.tick_params(axis='x', bottom=False)

ax.legend(frameon=False, labelcolor=LABEL_C, fontsize=9.5, loc='upper right')

ax.set_title('Success rate by athleticism band and draft round  (2010–2020)',
             color=LABEL_C, fontsize=11, pad=14, loc='left')

fig.tight_layout(pad=1.4)
out2 = os.path.join(OUT_DIR, 'sparq-success-rate.png')
fig.savefig(out2, dpi=160, facecolor=BG, bbox_inches='tight')
plt.close(fig)
print(f'Saved: {out2}')
