#!/usr/bin/env python3
"""
Hero image for the SF 49ers Lynch-era post.
A horizontal timeline of all 10 draft classes, colored by SPARQ tier,
with Super Bowl years marked in gold.
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'blogs', 'sf-49ers-lynch-era-sparq')
os.makedirs(OUT_DIR, exist_ok=True)

BG      = '#0a0c16'
SF_RED  = '#AA0000'
SF_GOLD = '#B3995D'

classes = [
    (2017, +0.48, None),
    (2018, +0.39, None),
    (2019, +0.09, 'SB'),
    (2020, -0.46, None),
    (2021, +0.18, 'NFCCG'),
    (2022, +0.08, 'NFCCG'),
    (2023, +0.13, 'SB'),
    (2024, +0.64, None),
    (2025, +0.60, None),
    (2026, +0.82, None),
]

fig = plt.figure(figsize=(14, 4.5), facecolor=BG)
ax  = fig.add_axes([0, 0, 1, 1])
ax.set_facecolor(BG)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis('off')

n = len(classes)
col_w = 1.0 / n

for i, (year, sparq, outcome) in enumerate(classes):
    x0 = i * col_w
    xc = x0 + col_w / 2

    # Panel color based on SPARQ
    if outcome in ('SB',):
        panel_bg  = '#1a1400'
        bar_color = SF_GOLD
        text_col  = SF_GOLD
    elif sparq >= 0.50:
        panel_bg  = '#160808'
        bar_color = SF_RED
        text_col  = '#e08080'
    elif sparq >= 0.00:
        panel_bg  = '#0f0d10'
        bar_color = '#7a4a4a'
        text_col  = '#aa8888'
    else:
        panel_bg  = '#080808'
        bar_color = '#3a2828'
        text_col  = '#664444'

    # Background panel
    rect = mpatches.FancyBboxPatch(
        (x0 + 0.004, 0.04), col_w - 0.008, 0.92,
        boxstyle='round,pad=0.005',
        facecolor=panel_bg, edgecolor=bar_color, linewidth=0.8, alpha=0.95,
        transform=ax.transAxes, zorder=1
    )
    ax.add_patch(rect)

    # Year
    ax.text(xc, 0.88, str(year),
            ha='center', va='top', fontsize=11, fontweight='900',
            color=text_col, transform=ax.transAxes,
            fontfamily='monospace', zorder=3)

    # SPARQ value
    zstr = f'+{sparq:.2f}' if sparq >= 0 else f'{sparq:.2f}'
    ax.text(xc, 0.72, zstr,
            ha='center', va='top', fontsize=14, fontweight='900',
            color=text_col, transform=ax.transAxes,
            fontfamily='monospace', zorder=3)

    # Mini bar (vertical, centered)
    bar_h = abs(sparq) * 0.28
    bar_y = 0.40 if sparq >= 0 else 0.40 - bar_h
    bar_rect = mpatches.Rectangle(
        (xc - 0.025, bar_y), 0.05, bar_h,
        facecolor=bar_color, alpha=0.7,
        transform=ax.transAxes, zorder=2
    )
    ax.add_patch(bar_rect)
    # zero line
    ax.plot([x0 + 0.01, x0 + col_w - 0.01], [0.40, 0.40],
            color='#2a2e40', linewidth=0.7, transform=ax.transAxes, zorder=2)

    # Outcome badge
    if outcome == 'SB':
        ax.text(xc, 0.18, 'SUPER\nBOWL',
                ha='center', va='center', fontsize=7.5, fontweight='900',
                color=SF_GOLD, alpha=0.9, transform=ax.transAxes,
                fontfamily='monospace', linespacing=1.2, zorder=3)
    elif outcome == 'NFCCG':
        ax.text(xc, 0.20, 'NFCCG',
                ha='center', va='center', fontsize=7, fontweight='700',
                color='#7abf9e', alpha=0.8, transform=ax.transAxes,
                fontfamily='monospace', zorder=3)

# Title
ax.text(0.012, 0.985, 'SAN FRANCISCO 49ERS  --  JOHN LYNCH ERA  --  SPARQ DRAFT PROFILE  2017-2026',
        ha='left', va='top', fontsize=8.5, fontweight='700',
        color='#334455', transform=ax.transAxes,
        fontfamily='monospace', zorder=4)

out = os.path.join(OUT_DIR, 'hero.jpg')
fig.savefig(out, dpi=180, facecolor=BG, bbox_inches='tight',
            pil_kwargs={'quality': 92})
plt.close(fig)
print(f'Saved: {out}')
