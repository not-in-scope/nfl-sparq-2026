#!/usr/bin/env python3
"""
Starter rate analysis by SPARQ tier x draft round.

Metric: did a player average 50%+ of their team's snaps in a season?
- Impact player: 3+ starter seasons
- Starter:       1-2 starter seasons
- Contributor:   appeared in games but never 50%+ snaps
- Bust:          rarely played (< 8 career games with snaps)
"""
import csv, io, json, os, sys
import requests
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from scrape import _norm_name

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
OUT_DIR  = os.path.join(os.path.dirname(__file__), '..', 'blogs', 'low-sparq-nfl-success')
HEADERS  = {'User-Agent': 'Mozilla/5.0 (compatible; nfl-sparq-analysis/1.0)'}

# ── Step 1: build pfr_id -> norm_name bridge from players.csv ────────────────

print("Loading players.csv pfr bridge...")
url = 'https://github.com/nflverse/nflverse-data/releases/download/players/players.csv'
r = requests.get(url, headers=HEADERS, timeout=40, allow_redirects=True)
pfr_to_norm = {}
for row in csv.DictReader(io.StringIO(r.text)):
    pfr = row.get('pfr_id', '').strip()
    name = row.get('display_name', '').strip()
    if pfr and name:
        pfr_to_norm[pfr] = _norm_name(name)
print(f"  pfr bridge: {len(pfr_to_norm)} entries")

# ── Step 2: fetch snap counts 2013-2025 ──────────────────────────────────────

print("Fetching snap counts 2013-2025...")
snap_seasons: dict[str, list] = defaultdict(list)

for year in range(2013, 2026):
    url = f'https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_{year}.csv'
    try:
        r = requests.get(url, headers=HEADERS, timeout=40, allow_redirects=True)
        if r.status_code != 200:
            print(f'  {year}: skip ({r.status_code})')
            continue
        rows = [row for row in csv.DictReader(io.StringIO(r.text))
                if row.get('game_type') == 'REG']

        player_games: dict[str, list] = defaultdict(list)
        for row in rows:
            pfr_id = row.get('pfr_player_id', '').strip()
            norm = pfr_to_norm.get(pfr_id) or _norm_name(row.get('player', '').strip())
            if not norm:
                continue
            off = float(row.get('offense_pct') or 0)
            dff = float(row.get('defense_pct') or 0)
            player_games[norm].append(max(off, dff))

        for norm, games in player_games.items():
            if len(games) < 4:
                continue
            avg_pct = sum(games) / len(games)
            snap_seasons[norm].append((year, avg_pct, len(games)))

        print(f'  {year}: {len(player_games)} players')
    except Exception as e:
        print(f'  {year}: error {e}')

print(f"Total players tracked: {len(snap_seasons)}")

# ── Step 3: classify each player ─────────────────────────────────────────────

def classify_player(seasons: list) -> str:
    total_games = sum(n for _, _, n in seasons)
    if total_games < 8:
        return 'Bust'
    starter_seasons = sum(1 for _, pct, _ in seasons if pct >= 0.50)
    if starter_seasons >= 3:
        return 'Impact'
    if starter_seasons >= 1:
        return 'Starter'
    return 'Contributor'

player_class = {norm: classify_player(seasons) for norm, seasons in snap_seasons.items()}

# ── Step 4: load prospects 2010-2020 with SPARQ ───────────────────────────────

print("\nLoading prospects 2010-2020...")
players = []
for year in range(2010, 2021):
    path = os.path.join(DATA_DIR, f'prospects_{year}.json')
    if not os.path.exists(path):
        continue
    for p in json.load(open(path))['prospects']:
        if p.get('z_score') is None or not p.get('draft_round'):
            continue
        norm = _norm_name(p['name'])
        cls = player_class.get(norm, 'Bust')
        players.append({
            'name':    p['name'],
            'z_score': p['z_score'],
            'round':   p['draft_round'],
            'class':   cls,
        })

matched = sum(1 for p in players if _norm_name(p['name']) in player_class)
print(f"Matched: {matched} / {len(players)} ({matched/len(players)*100:.0f}%)")

def sparq_band(z):
    if   z >= 0.674:  return 'High SPARQ\n(top 25%)'
    elif z >= -0.674: return 'Mid SPARQ\n(middle 50%)'
    else:             return 'Low SPARQ\n(bottom 25%)'

def round_grp(r):
    if r <= 2:  return 'R1-2'
    if r <= 5:  return 'R3-5'
    return 'R6-7'

for p in players:
    p['band']  = sparq_band(p['z_score'])
    p['rgrp']  = round_grp(p['round'])

# ── Step 5: compute stats ─────────────────────────────────────────────────────

BANDS  = ['High SPARQ\n(top 25%)', 'Mid SPARQ\n(middle 50%)', 'Low SPARQ\n(bottom 25%)']
RGRPS  = ['R1-2', 'R3-5', 'R6-7']
CLSS   = ['Impact', 'Starter', 'Contributor', 'Bust']

counts = defaultdict(lambda: defaultdict(int))
for p in players:
    counts[(p['band'], p['rgrp'])][p['class']] += 1

print("\n--- Starter rate summary ---")
for band in BANDS:
    for rgrp in RGRPS:
        c = counts[(band, rgrp)]
        n = sum(c.values())
        if n == 0:
            continue
        impact  = c['Impact'] / n * 100
        starter = (c['Impact'] + c['Starter']) / n * 100
        label   = band.replace('\n', ' ')
        print(f"{label:30} {rgrp}: n={n:4}  impact={impact:.0f}%  ever_starter={starter:.0f}%")

# ── Step 6: visualize ─────────────────────────────────────────────────────────

BG      = '#0d0f1a'
TEXT_C  = '#8899bb'
LABEL_C = '#c8d4f0'
GRID_C  = '#1a1e30'

C_COLORS = {
    'Impact':      '#4a7fd4',
    'Starter':     '#3a9e6e',
    'Contributor': '#c8a040',
    'Bust':        '#c04a4a',
}

def style_ax(ax):
    ax.set_facecolor(BG)
    ax.tick_params(colors=TEXT_C, labelsize=10)
    for spine in ['bottom', 'left']:
        ax.spines[spine].set_color(GRID_C)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, color=GRID_C, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)

# ── Chart A: stacked bar — starter class by SPARQ band × round group ──────────

fig, axes = plt.subplots(1, 3, figsize=(13, 5.5), facecolor=BG, sharey=True)
fig.subplots_adjust(wspace=0.06)

for ai, rgrp in enumerate(RGRPS):
    ax = axes[ai]
    style_ax(ax)
    x = np.arange(len(BANDS))
    bar_w = 0.55
    bottoms = np.zeros(len(BANDS))

    for cls in CLSS:
        vals = np.array([counts[(b, rgrp)][cls] for b in BANDS], dtype=float)
        tots = np.array([sum(counts[(b, rgrp)].values()) for b in BANDS], dtype=float)
        tots[tots == 0] = 1
        pcts = vals / tots * 100
        ax.bar(x, pcts, bar_w, bottom=bottoms, color=C_COLORS[cls], zorder=3, alpha=0.90)
        for i, (pct, bot) in enumerate(zip(pcts, bottoms)):
            if pct >= 10:
                ax.text(x[i], bot + pct / 2, f'{pct:.0f}%',
                        ha='center', va='center', fontsize=8.5,
                        color='white', alpha=0.88, fontweight='600')
        bottoms += pcts

    for i, band in enumerate(BANDS):
        n = sum(counts[(band, rgrp)].values())
        ax.text(x[i], 101.5, f'n={n}', ha='center', va='bottom', fontsize=7.5, color=TEXT_C)

    ax.set_xticks(x)
    short = ['High\nSPARQ', 'Mid\nSPARQ', 'Low\nSPARQ']
    ax.set_xticklabels(short, color=LABEL_C, fontsize=9.5)
    ax.set_ylim(0, 109)
    ax.tick_params(axis='x', bottom=False)
    ax.set_title(rgrp, color=LABEL_C, fontsize=12, fontweight='700', pad=10)
    if ai == 0:
        ax.set_ylabel('% of players', color=TEXT_C, fontsize=10)

patches = [mpatches.Patch(color=C_COLORS[c], label=c) for c in CLSS]
fig.legend(handles=patches, frameon=False, labelcolor=LABEL_C, fontsize=9.5,
           loc='lower center', bbox_to_anchor=(0.5, -0.04), ncol=4,
           handlelength=1.2, handleheight=0.9)
fig.suptitle('Did they actually start? Career snap-share class by SPARQ band and draft round',
             color=LABEL_C, fontsize=11, y=1.01, x=0.07, ha='left')

fig.tight_layout(rect=[0, 0.06, 1, 1])
out_a = os.path.join(OUT_DIR, 'sparq-starter-rate.png')
fig.savefig(out_a, dpi=160, facecolor=BG, bbox_inches='tight')
plt.close(fig)
print(f'\nSaved: {out_a}')

# ── Chart B: impact rate line by SPARQ × round ───────────────────────────────

fig, ax = plt.subplots(figsize=(9, 5), facecolor=BG)
style_ax(ax)

x = np.arange(len(RGRPS))
band_styles = [
    ('High SPARQ\n(top 25%)',   '#4a7fd4', 'o', 'High SPARQ'),
    ('Mid SPARQ\n(middle 50%)', '#3a9e6e', 's', 'Mid SPARQ'),
    ('Low SPARQ\n(bottom 25%)', '#c8a040', '^', 'Low SPARQ'),
]

for band, color, marker, label in band_styles:
    rates, ns = [], []
    for rgrp in RGRPS:
        c = counts[(band, rgrp)]
        n = sum(c.values())
        rate = c['Impact'] / n * 100 if n else 0
        rates.append(rate)
        ns.append(n)
    ax.plot(x, rates, color=color, marker=marker, linewidth=2.2,
            markersize=8, label=label, zorder=4)
    for xi, (rate, n) in enumerate(zip(rates, ns)):
        ax.text(xi, rate + 2.5, f'{rate:.0f}%\n(n={n})', ha='center', fontsize=8.5,
                color=color, fontweight='600')

ax.set_xticks(x)
ax.set_xticklabels(['Rounds 1-2', 'Rounds 3-5', 'Rounds 6-7'], color=LABEL_C, fontsize=11)
ax.set_ylabel('% who became Impact starters\n(3+ seasons at 50%+ snaps)', color=TEXT_C, fontsize=10)
ax.set_ylim(0, 90)
ax.tick_params(axis='x', bottom=False)
ax.legend(frameon=False, labelcolor=LABEL_C, fontsize=10, loc='upper right')
ax.set_title('Impact starter rate by athleticism and draft round   (2010-2020 classes)',
             color=LABEL_C, fontsize=11, pad=12, loc='left')

fig.tight_layout(pad=1.4)
out_b = os.path.join(OUT_DIR, 'sparq-impact-rate.png')
fig.savefig(out_b, dpi=160, facecolor=BG, bbox_inches='tight')
plt.close(fig)
print(f'Saved: {out_b}')
