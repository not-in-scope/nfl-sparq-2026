#!/usr/bin/env python3
"""
Point-in-time validation: 2021 and 2022 draft classes.
For each team: what was their avg SPARQ at draft time, and what % of those
picks became NFL starters 2-4 years later?

Starter = at least 1 season averaging 50%+ snap share (offense or defense).
Uses nflverse snap_counts 2021-2024.
"""
import csv, io, json, os, sys
import requests
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from scrape import _norm_name

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
OUT_DIR  = os.path.join(os.path.dirname(__file__), '..', 'blogs', 'sparq-draft-grades-2026')
HEADERS  = {'User-Agent': 'Mozilla/5.0 (compatible; nfl-sparq-analysis/1.0)'}

BG      = '#0d0f1a'
TEXT_C  = '#8899bb'
LABEL_C = '#c8d4f0'
GRID_C  = '#1a1e30'

# ── pfr bridge ─────────────────────────────────────────────────────────────────
print("Loading pfr bridge...")
url = 'https://github.com/nflverse/nflverse-data/releases/download/players/players.csv'
r = requests.get(url, headers=HEADERS, timeout=40, allow_redirects=True)
pfr_to_norm = {}
for row in csv.DictReader(io.StringIO(r.text)):
    pfr = row.get('pfr_id', '').strip()
    name = row.get('display_name', '').strip()
    if pfr and name:
        pfr_to_norm[pfr] = _norm_name(name)
print(f"  {len(pfr_to_norm)} entries")

# ── snap counts 2021-2024 ──────────────────────────────────────────────────────
print("Fetching snap counts 2021-2024...")
snap_seasons: dict[str, list] = defaultdict(list)

for year in range(2021, 2025):
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
            snap_seasons[norm].append((year, sum(games) / len(games), len(games)))

        print(f'  {year}: {len(player_games)} players')
    except Exception as e:
        print(f'  {year}: error {e}')

print(f"Total players with snap data: {len(snap_seasons)}")

def is_starter(norm: str) -> bool | None:
    """True = became a starter, False = played but didn't start, None = no data."""
    seasons = snap_seasons.get(norm)
    if not seasons:
        return None
    total_games = sum(n for _, _, n in seasons)
    if total_games < 8:
        return None
    return any(pct >= 0.50 for _, pct, _ in seasons)

# ── 2021 and 2022 prospects grouped by team ────────────────────────────────────
print("\nComputing team outcomes...")
team_data: dict[tuple, dict] = {}

for draft_year in [2021, 2022]:
    path = os.path.join(DATA_DIR, f'prospects_{draft_year}.json')
    d = json.load(open(path))
    prospects = d.get('prospects', d) if isinstance(d, dict) else d

    for p in prospects:
        if p.get('round_source') != 'actual':
            continue
        team = p.get('team')
        z    = p.get('z_score')
        if not team:
            continue

        key = (draft_year, team)
        if key not in team_data:
            team_data[key] = {'sparq': [], 'started': 0, 'tracked': 0, 'total': 0}

        team_data[key]['total'] += 1
        if z is not None:
            team_data[key]['sparq'].append(z)

        norm   = _norm_name(p['name'])
        result = is_starter(norm)
        if result is not None:
            team_data[key]['tracked'] += 1
            if result:
                team_data[key]['started'] += 1

# Build plottable rows
rows_21, rows_22 = [], []
for (yr, team), d in team_data.items():
    if len(d['sparq']) < 2 or d['tracked'] < 3:
        continue
    sparq_avg   = sum(d['sparq']) / len(d['sparq'])
    starter_pct = d['started'] / d['tracked'] * 100
    entry = (team, sparq_avg, starter_pct, d['tracked'], d['total'])
    if yr == 2021:
        rows_21.append(entry)
    else:
        rows_22.append(entry)

print(f"  2021: {len(rows_21)} teams    2022: {len(rows_22)} teams")

# Combined for correlation
all_rows = rows_21 + rows_22
sparqs  = [r[1] for r in all_rows]
strates = [r[2] for r in all_rows]
corr = np.corrcoef(sparqs, strates)[0, 1] if len(all_rows) >= 4 else 0.0
print(f"  Correlation SPARQ avg vs starter_rate: r={corr:.3f} (n={len(all_rows)} team-years)")

# ── Print summary ──────────────────────────────────────────────────────────────
print("\n--- Top SPARQ, high starter rate ---")
for team, sparq, sr, tracked, total in sorted(all_rows, key=lambda x: x[1], reverse=True)[:8]:
    print(f"  {team}: sparq={sparq:+.2f}  starter_rate={sr:.0f}%  ({tracked}/{total} tracked)")

print("\n--- Low SPARQ teams ---")
for team, sparq, sr, tracked, total in sorted(all_rows, key=lambda x: x[1])[:8]:
    print(f"  {team}: sparq={sparq:+.2f}  starter_rate={sr:.0f}%  ({tracked}/{total} tracked)")

# ── Figure: scatter SPARQ avg vs starter rate ──────────────────────────────────
fig, ax = plt.subplots(figsize=(11, 6.5), facecolor=BG)
ax.set_facecolor(BG)
ax.spines['bottom'].set_color(GRID_C)
ax.spines['left'].set_color(GRID_C)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.tick_params(colors=TEXT_C, labelsize=9.5)
ax.yaxis.grid(True, color=GRID_C, linewidth=0.5, zorder=0)
ax.xaxis.grid(True, color=GRID_C, linewidth=0.5, zorder=0)
ax.set_axisbelow(True)

C21 = '#4a7fd4'   # 2021 — blue
C22 = '#3a9e6e'   # 2022 — green

# Regression line
if len(all_rows) >= 4:
    m, b = np.polyfit(sparqs, strates, 1)
    xs = np.linspace(min(sparqs) - 0.1, max(sparqs) + 0.1, 100)
    ax.plot(xs, m * xs + b, color='#2a3050', linewidth=1.5, linestyle='--', zorder=2, alpha=0.7)

offsets_21 = {'KC': (0.04, 3), 'NYG': (-0.04, 3), 'SEA': (0.04, -5),
               'CLE': (0.04, -5), 'NYJ': (-0.04, 3), 'DAL': (0.04, 3)}
offsets_22 = {}

for rows, color, yr in [(rows_21, C21, '21'), (rows_22, C22, '22')]:
    off_dict = offsets_21 if yr == '21' else offsets_22
    ax.scatter([r[1] for r in rows], [r[2] for r in rows],
               c=color, s=55, zorder=4, alpha=0.85)
    for team, sparq, sr, tracked, _ in rows:
        dx, dy = off_dict.get(team, (0.04, 3))
        ax.text(sparq + dx, sr + dy, f"{team}'{yr}",
                ha='left' if dx >= 0 else 'right', va='center',
                fontsize=7.5, color=color, alpha=0.85,
                fontfamily='monospace', fontweight='600', zorder=5)

# Legend dots
ax.scatter([], [], c=C21, s=55, label="2021 draft class")
ax.scatter([], [], c=C22, s=55, label="2022 draft class")
ax.legend(frameon=False, labelcolor=LABEL_C, fontsize=9.5, loc='upper left')

ax.set_xlabel('SPARQ z-score (avg of picks with combine data at time of draft)',
              color=TEXT_C, fontsize=10, labelpad=10)
ax.set_ylabel('% of tracked picks who became NFL starters\n(at least 1 season at 50%+ snap share)',
              color=TEXT_C, fontsize=10, labelpad=10)
ax.set_title(
    f'Did SPARQ predict draft success?   2021-2022 classes   (r={corr:.2f})',
    color=LABEL_C, fontsize=11, pad=14, loc='left')

# Annotation
note = (
    "Each dot = one team's draft class. Starter = 50%+ snap share\n"
    "in at least one season through 2024. r = Pearson correlation."
)
ax.text(0.98, 0.04, note, transform=ax.transAxes, ha='right', va='bottom',
        fontsize=8, color=TEXT_C, alpha=0.6, style='italic')

fig.tight_layout(pad=1.6)
out = os.path.join(OUT_DIR, 'sparq-historical-validation.png')
fig.savefig(out, dpi=160, facecolor=BG, bbox_inches='tight')
plt.close(fig)
print(f'\nSaved: {out}')
