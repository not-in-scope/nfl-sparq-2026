# 2026 NFL Draft SPARQ Rankings

SPARQ athleticism scores for all ~458 2026 NFL Draft prospects. Live at:
**https://not-in-scope.github.io/nfl-sparq-2026/**

## Refresh data

```bash
pip install -r scripts/requirements.txt
python scripts/scrape.py
git add data/prospects.json
git commit -m "data: refresh SPARQ scores $(date +%Y-%m-%d)"
git push
```

## Post-draft update (after April 25, 2026)

```bash
python scripts/scrape.py --add-draft-results
git add data/prospects.json
git commit -m "data: update with actual draft picks"
git push
```
