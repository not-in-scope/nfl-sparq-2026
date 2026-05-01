import json, os

DATA_DIR = 'data'

results = {}
for year in range(2017, 2027):
    path = os.path.join(DATA_DIR, f'prospects_{year}.json')
    if not os.path.exists(path):
        continue
    d = json.load(open(path))
    prospects = d.get('prospects', d) if isinstance(d, dict) else d

    sf_picks = [p for p in prospects if p.get('team') == 'SF' and p.get('round_source') == 'actual']
    sf_scored = [p for p in sf_picks if p.get('z_score') is not None]

    if sf_picks:
        avg_z = sum(p['z_score'] for p in sf_scored) / len(sf_scored) if sf_scored else None
        results[year] = {
            'total': len(sf_picks),
            'scored': len(sf_scored),
            'avg_z': avg_z,
            'picks': [(p['name'], p['pos'], p.get('draft_round','?'), round(p['z_score'],2) if p.get('z_score') is not None else None) for p in sf_picks]
        }

for yr, d in results.items():
    z = d['avg_z']
    zstr = (f"+{z:.2f}" if z > 0 else f"{z:.2f}") if z is not None else "N/A"
    print(f"{yr}: total={d['total']} scored={d['scored']} avg_z={zstr}")
    for name, pos, rnd, zs in d['picks']:
        zsstr = (f"+{zs:.2f}" if zs and zs > 0 else f"{zs:.2f}") if zs is not None else "no data"
        print(f"   R{rnd} {pos} {name}: {zsstr}")
    print()
