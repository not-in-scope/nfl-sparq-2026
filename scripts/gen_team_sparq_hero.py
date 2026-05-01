#!/usr/bin/env python3
"""
Generate a custom hero image for the team SPARQ grades post.
A tier board showing all 32 teams grouped by SPARQ tier.
"""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
OUT_DIR  = os.path.join(os.path.dirname(__file__), '..', 'blogs', 'sparq-draft-grades-2026')

# ── Colors ────────────────────────────────────────────────────────────────────
BG       = '#0a0c16'
TIERS = [
    ('BUILT\nDIFFERENT', 1.0,   '#4a7fd4', '#0d1a2e'),
    ('ON\nTREND',        0.7,   '#3a9e6e', '#0d2018'),
    ('FILM\nFIRST',      0.4,   '#c8a040', '#201a0a'),
    ('GAMBLING\nON SKILL',-99,  '#c04a4a', '#200d0d'),
]

# ── Load and compute team averages ────────────────────────────────────────────
prospects = json.load(open(os.path.join(DATA_DIR, 'prospects_2026.json')))['prospects']

team_scores = defaultdict(list)
for p in prospects:
    if p.get('round_source') != 'actual':
        continue
    team = p.get('team')
    z    = p.get('z_score')
    if team and z is not None:
        team_scores[team].append(z)

team_avgs = {t: sum(s)/len(s) for t, s in team_scores.items() if len(s) >= 2}
ranked = sorted(team_avgs.items(), key=lambda x: x[1], reverse=True)

def get_tier(z):
    for label, threshold, color, bg in TIERS:
        if z >= threshold:
            return label, color, bg
    return TIERS[-1][0], TIERS[-1][2], TIERS[-1][3]

# Group teams by tier
tier_teams = {t[0]: [] for t in TIERS}
for team, avg in ranked:
    label, color, bg = get_tier(avg)
    tier_teams[label].append((team, avg))

# ── Figure ─────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(14, 5), facecolor=BG)
ax  = fig.add_axes([0, 0, 1, 1])
ax.set_facecolor(BG)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis('off')

tier_positions = [0.0, 0.25, 0.52, 0.74]  # x start of each tier block
tier_widths    = [0.25, 0.27, 0.22, 0.26]

for i, (label, threshold, color, bg_col) in enumerate(TIERS):
    x0 = tier_positions[i]
    w  = tier_widths[i]
    teams_in_tier = tier_teams[label]

    # Tier background panel
    rect = mpatches.FancyBboxPatch(
        (x0 + 0.005, 0.02), w - 0.01, 0.96,
        boxstyle='round,pad=0.01',
        facecolor=bg_col, edgecolor=color, linewidth=1.2, alpha=0.9,
        transform=ax.transAxes, zorder=1
    )
    ax.add_patch(rect)

    # Tier label
    ax.text(x0 + w / 2, 0.88, label,
            ha='center', va='top', fontsize=11, fontweight='900',
            color=color, transform=ax.transAxes,
            fontfamily='monospace', linespacing=1.3,
            zorder=3)

    # Divider line under label
    ax.plot([x0 + 0.02, x0 + w - 0.02], [0.72, 0.72],
            color=color, linewidth=0.8, alpha=0.4,
            transform=ax.transAxes, zorder=3)

    # Team abbreviations
    cols = 2 if len(teams_in_tier) > 4 else 1
    per_col = -(-len(teams_in_tier) // cols)  # ceiling div

    col_w = (w - 0.04) / cols
    for j, (team, avg) in enumerate(teams_in_tier):
        col = j // per_col
        row = j % per_col
        tx = x0 + 0.02 + col * col_w + col_w / 2
        ty = 0.64 - row * 0.115

        # Team abbr
        ax.text(tx, ty, team,
                ha='center', va='center', fontsize=13.5, fontweight='800',
                color=color, alpha=0.95, transform=ax.transAxes,
                fontfamily='monospace', zorder=3)

        # z-score subscript
        ax.text(tx, ty - 0.055, f'{avg:+.2f}',
                ha='center', va='center', fontsize=7.5,
                color=color, alpha=0.45, transform=ax.transAxes,
                fontfamily='monospace', zorder=3)

# Title area — left aligned, top
ax.text(0.012, 0.995, '2026 NFL DRAFT  --  SPARQ TIER BOARD',
        ha='left', va='top', fontsize=9, fontweight='700',
        color='#445566', transform=ax.transAxes,
        fontfamily='monospace', zorder=4)

out = os.path.join(OUT_DIR, 'hero.jpg')
fig.savefig(out, dpi=180, facecolor=BG, bbox_inches='tight',
            pil_kwargs={'quality': 92})
plt.close(fig)
print(f'Saved: {out}')
