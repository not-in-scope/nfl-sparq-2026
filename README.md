# NFL SPARQ Rankings

Athleticism scores for NFL Draft prospects across all years (2010–2026), ranked by **pSPARQ** — a community-derived approximation of Nike's SPARQ formula.

**Live site:** https://not-in-scope.github.io/nfl-sparq/

---

## What is SPARQ?

SPARQ (Speed, Power, Agility, Reaction, Quickness) is a composite athleticism score originally developed by Nike. It combines NFL Combine measurements into a single number that quantifies raw physical ability independent of football skill or scheme fit.

This project uses **pSPARQ** — a community approximation of the formula, validated against known scores and cross-referenced with [3sigmaathlete.com](https://3sigmaathlete.com), which pioneered the use of SPARQ for NFL prospect evaluation. Positional norms and z-score methodology are adapted from their work.

The formula weights:

| Metric | Role |
|--------|------|
| Weight | Base athleticism anchor |
| Vertical jump | Lower-body explosion |
| Broad jump | Horizontal power |
| Bench press | Upper-body strength |
| 40-yard dash | Straight-line speed |
| 3-cone drill | Change of direction |
| 20-yard shuttle | Lateral quickness |

---

## What is σ (sigma)?

A raw pSPARQ score means little without context — a 110 is elite for an OT and average for a WR. The **σ (z-score)** normalizes each score against historical combine data for that position (1999–2023), so you can compare athleticism across positions on the same scale:

| σ | Tier |
|---|------|
| ≥ 2.0 | Elite |
| 1.0 – 2.0 | Above Average |
| 0.0 – 1.0 | Average |
| −2.0 – 0.0 | Below Average |
| < −2.0 | Poor |

---

## Data sources

- **Combine measurements** — [BigBoardLab](https://bigboardlab.com) (2026), [nflcombineresults.com](https://nflcombineresults.com) (historical)
- **Pro day data** — [MockDraftable](https://mockdraftable.com), [PFF Pro Day Tracker](https://pff.com)
- **Draft picks & positions** — [ESPN Draft API](https://sports.core.api.espn.com)
- **pSPARQ formula & positional norms** — adapted from [3sigmaathlete.com](https://3sigmaathlete.com)

---

## Data pipeline

```
BigBoardLab / nflcombineresults
        ↓
MockDraftable (pro day enrichment)
        ↓
PFF pro day tracker
        ↓
ESPN draft board (picks + positions)
        ↓
Sanitize metrics (bounds checking)
        ↓
Estimate missing inputs (positional medians)
        ↓
Compute pSPARQ → z-score → percentile
```

Missing drills are imputed from positional medians before scoring. Players need at least 4 real measurements (combine or pro day) to receive a score.

---

## Refresh data

```bash
pip install -r scripts/requirements.txt

# Current year (2026)
python scripts/scrape.py

# Historical year
python scripts/scrape.py --year 2020
```

---

## Credits

pSPARQ formula and positional z-score methodology adapted from [**3sigmaathlete.com**](https://3sigmaathlete.com). Their work on applying SPARQ to NFL Draft evaluation is the foundation this project builds on.
