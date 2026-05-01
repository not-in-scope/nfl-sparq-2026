#!/usr/bin/env python3
"""
Bar chart: SF 49ers avg SPARQ z-score per Lynch-era draft class (2017-2026).
Annotated with key picks and season outcomes.
"""
import json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
OUT_DIR  = os.path.join(os.path.dirname(__file__), '..', 'blogs', 'sf-49ers-lynch-era-sparq')
os.makedirs(OUT_DIR, exist_ok=True)

BG      = '#0d0f1a'
TEXT_C  = '#8899bb'
LABEL_C = '#c8d4f0'
GRID_C  = '#1a1e30'
SF_RED  = '#AA0000'
SF_GOLD = '#B3995D'

# ── SPARQ data (precomputed) ───────────────────────────────────────────────────
classes = [
    # year, avg_z, n_scored, n_total, key_picks, season_record, playoff_result
    (2017, +0.48, 9, 10, ['G. Kittle R5', 'S. Thomas R1 (+2.32)', 'C.J. Beathard R3'],
     '6-10', None),
    (2018, +0.39, 6,  9, ['F. Warner R3 (+1.00)', 'M. McGlinchey R1', 'D. Pettis R2'],
     '4-12', None),
    (2019, +0.09, 7,  8, ['N. Bosa R1 (+1.01)', 'D. Samuel R2', 'D. Greenlaw R5'],
     '13-3', 'Super Bowl'),
    (2020, -0.46, 4,  5, ['B. Aiyuk R1 (+0.23)', 'J. Kinlaw R1', 'J. Jennings R7'],
     '6-10', None),
    (2021, +0.18, 6,  7, ['T. Lance R1', 'T. Hufanga R5', 'E. Mitchell R6 (+0.92)'],
     '10-7', 'NFC Champ'),
    (2022, +0.08, 5,  8, ['B. Purdy R7 (-0.05)', 'D. Jackson R2', 'D. Davis-Price R3'],
     '13-4', 'NFC Champ'),
    (2023, +0.13, 7,  7, ['C. Latu R3', 'D. Luter R5', 'B. Willis R7 (+0.78)'],
     '12-5', 'Super Bowl'),
    (2024, +0.64, 8,  8, ['R. Pearsall R1 (+0.97)', 'I. Guerendo R4 (+1.58)', 'M. Mustapha R4 (+1.37)'],
     '6-11', None),
    (2025, +0.60, 7, 10, ['M. Williams R1', 'N. Martin R3 (+1.48)', 'C.J. West R4 (+1.30)'],
     'TBD', None),
    (2026, +0.82, 8,  8, ['R. Height R3 (+1.20)', 'K. Black R3 (+1.41)', 'G. Halton R4 (+1.18)'],
     'TBD', None),
]

years    = [c[0] for c in classes]
avgs     = [c[1] for c in classes]
n_scored = [c[2] for c in classes]
n_total  = [c[3] for c in classes]
records  = [c[5] for c in classes]
playoffs = [c[6] for c in classes]

# ── Bar colors: good (>= 0.40) = SF red; decent (0.10-0.39) = muted; low = dim
def bar_color(z):
    if z >= 0.40: return '#c0392b'   # SF red-ish
    if z >= 0.00: return '#7a4a4a'   # muted warm
    return '#3a2828'                  # near-black for negative

colors = [bar_color(z) for z in avgs]
# 2026 gets gold highlight
colors[-1] = SF_GOLD
colors[-2] = '#9a7a3a'  # 2025 muted gold

# ── Figure ─────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 6.5), facecolor=BG)
ax.set_facecolor(BG)
ax.spines['bottom'].set_color(GRID_C)
ax.spines['left'].set_color(GRID_C)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.tick_params(colors=TEXT_C, labelsize=10)
ax.yaxis.grid(True, color=GRID_C, linewidth=0.5, zorder=0)
ax.set_axisbelow(True)

x = np.arange(len(years))
bars = ax.bar(x, avgs, color=colors, width=0.65, zorder=3, alpha=0.92)

# Zero line
ax.axhline(0, color=GRID_C, linewidth=1.0, zorder=2)

# Value labels above/below bars
for i, (avg, bar) in enumerate(zip(avgs, bars)):
    label = f'+{avg:.2f}' if avg >= 0 else f'{avg:.2f}'
    ypos = avg + 0.03 if avg >= 0 else avg - 0.06
    va = 'bottom' if avg >= 0 else 'top'
    ax.text(bar.get_x() + bar.get_width() / 2, ypos, label,
            ha='center', va=va, fontsize=8.5, color=LABEL_C,
            fontfamily='monospace', fontweight='700', zorder=5)

# n= label inside bar
for i, (avg, n_s, n_t, bar) in enumerate(zip(avgs, n_scored, n_total, bars)):
    if abs(avg) < 0.12:
        continue
    ypos = avg / 2
    ax.text(bar.get_x() + bar.get_width() / 2, ypos,
            f'n={n_s}/{n_t}',
            ha='center', va='center', fontsize=7, color='white', alpha=0.5,
            fontfamily='monospace', zorder=5)

# Season record + playoff badges
for i, (rec, po) in enumerate(zip(records, playoffs)):
    y_badge = -0.62
    ax.text(x[i], y_badge, rec,
            ha='center', va='top', fontsize=8, color=TEXT_C,
            fontfamily='monospace', zorder=5)
    if po == 'Super Bowl':
        ax.text(x[i], -0.78, 'SB', ha='center', va='top',
                fontsize=7.5, color=SF_GOLD, fontweight='900',
                fontfamily='monospace', zorder=5)
    elif po == 'NFC Champ':
        ax.text(x[i], -0.78, 'NFCCG', ha='center', va='top',
                fontsize=7, color='#7abf9e', fontweight='700',
                fontfamily='monospace', zorder=5)

# Key pick annotations (one notable name per year)
key_picks_display = [
    'Kittle R5', 'F. Warner R3', 'Bosa / Samuel', 'Aiyuk / Kinlaw',
    'Trey Lance R1', 'Brock Purdy R7', 'Cam Latu R3', 'Pearsall / Guerendo',
    'Mykel Williams R1', 'Height / K. Black R3'
]
for i, label in enumerate(key_picks_display):
    ypos = avgs[i] + 0.16 if avgs[i] >= 0 else avgs[i] - 0.18
    va = 'bottom' if avgs[i] >= 0 else 'top'
    ax.text(x[i], ypos, label, ha='center', va=va,
            fontsize=7.5, color=TEXT_C, alpha=0.75,
            fontfamily='monospace', style='italic', zorder=5)

ax.set_xticks(x)
ax.set_xticklabels([str(y) for y in years], color=LABEL_C, fontsize=10.5,
                   fontfamily='monospace', fontweight='700')
ax.set_ylabel('Avg SPARQ z-score (scored picks only)',
              color=TEXT_C, fontsize=10, labelpad=10)
ax.set_ylim(-0.95, 1.45)
ax.set_title(
    'SF 49ers SPARQ draft grades, Lynch/Shanahan era   (2017-2026)',
    color=LABEL_C, fontsize=12, pad=14, loc='left')

# Legend note
ax.text(0.99, 0.98,
        'SB = Super Bowl appearance   NFCCG = NFC Championship',
        transform=ax.transAxes, ha='right', va='top',
        fontsize=8, color=TEXT_C, alpha=0.55, style='italic')

fig.tight_layout(pad=1.6)
out = os.path.join(OUT_DIR, 'sf-lynch-era-sparq.png')
fig.savefig(out, dpi=160, facecolor=BG, bbox_inches='tight')
plt.close(fig)
print(f'Saved: {out}')
