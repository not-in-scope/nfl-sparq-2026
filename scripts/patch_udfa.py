#!/usr/bin/env python3
"""One-off: apply 2026 UDFA signing teams and clear mock draft_round for players who went undrafted."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from scrape import _norm_name

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

UDFA_MAP_RAW = {
    # ARI
    "Elijah Culp": "ARI", "Tre Wallace": "ARI",
    # ATL
    "Jack Strand": "ATL", "Carlos Allen": "ATL", "James Brockermeyer": "ATL",
    "Malik Rutherford": "ATL", "Jack Velling": "ATL", "CJ Nunnally": "ATL",
    "Cash Jones": "ATL", "Vinny Anthony": "ATL", "Vinny Anthony II": "ATL",
    "Vincent Anthony Jr.": "ATL", "Riley Mahlman": "ATL", "Malcolm Dewalt": "ATL",
    # BAL
    "Reid Williford": "BAL", "Matthew McDoom": "BAL", "Nick Dawkins": "BAL",
    "Cortez Braham": "BAL", "Aaron Graves": "BAL", "Joey Fagnano": "BAL",
    "Joe Fagnano": "BAL", "Diego Pounds": "BAL", "Jahquez Robinson": "BAL",
    "Silas Walters": "BAL", "Ladarius Webb Jr.": "BAL", "Dontae McMillan": "BAL",
    "Octavion Smith Jr.": "BAL", "Trevonte Sylvester": "BAL",
    # BUF
    "Ja'Mori Maclin": "BUF", "Theron Gaines": "BUF",
    "Da'Metrius Weatherspoon": "BUF", "Desmond Reid": "BUF",
    # CAR
    "Haynes King": "CAR", "Jaylon Guilbreau": "CAR", "Jaylin Guilbeau": "CAR",
    "Cam Miller": "CAR", "Kobe Prentice": "CAR", "Aaron Hall": "CAR",
    # CHI
    "Miller Moss": "CHI", "KC Eziomume": "CHI", "Gabriel Plascencia": "CHI",
    "Hayden Large": "CHI", "Skyler Thomas": "CHI", "Caden Barnett": "CHI",
    "Coleman Bennett": "CHI",
    # CIN
    "Jack Dingle": "CIN", "Josh Kattus": "CIN", "Ceyair Wright": "CIN",
    "Corey Robinson": "CIN",
    # CLE
    "Logan Fano": "CLE", "Bernard Gooden": "CLE", "Tyreak Sapp": "CLE",
    "T.J. Harden": "CLE", "Davon Booth": "CLE", "DeCarlos Nicholson": "CLE",
    "Michael Coats Jr.": "CLE",
    # DAL
    "Jordan Hudson": "DAL", "DJ Rogers": "DAL", "Michael Trigg": "DAL",
    "Dominic Richardson": "DAL",
    # DEN
    "Taurean York": "DEN", "Dane Key": "DEN", "Brent Austin": "DEN",
    "Sidney Fulgar": "DEN", "Luke Basso": "DEN", "Sean Brown": "DEN",
    "Joseph Manjack IV": "DEN", "Dasan McCullough": "DEN",
    # DET
    "De'Shawn Rucker": "DET", "Luke Altmyer": "DET", "Melvin Priestly": "DET",
    "Aidan Keanaaina": "DET", "Erick Hunter": "DET",
    # GB
    "Kyron Drones": "GB", "TJ Quinn": "GB", "Murvin Kenion": "GB",
    "J. Michael Sturdivant": "GB", "Nyjalik Kelly": "GB", "RJ Maryland": "GB",
    # HOU
    "Jack Stonehouse": "HOU", "Noah Whittington": "HOU", "Jalen Walthall": "HOU",
    "Collin Wright": "HOU", "Sabastian Harsh": "HOU", "Daniel Sobkowicz": "HOU",
    "Stephen Hall": "HOU", "James Neal III": "HOU", "James Neal": "HOU",
    "Treyvhon Saunders": "HOU",
    # IND
    "Austin Brown": "IND", "West Weeks": "IND", "Seth McGowan": "IND",
    "Nolan Rucci": "IND", "Cameron Ball": "IND", "Cam Ball": "IND",
    # JAX
    "Joey Aguilar": "JAX", "Jalen Hunt": "JAX", "Ben Patterson": "JAX",
    "Alex Bullock": "JAX", "Bryan Thomas Jr.": "JAX", "Trebor Pena": "JAX",
    "Brady Boyd": "JAX", "Devon Marshall": "JAX",
    # KC
    "Jaydn Ott": "KC", "Pete Nygra": "KC", "Xavier Nwankpa": "KC",
    "John Michael Gyllenborg": "KC", "Josh Thompson": "KC",
    "Bryce Phillips": "KC", "Wesley Bissainthe": "KC", "VJ Anthony": "KC",
    "Jeff Caldwell": "KC", "DeShon Singleton": "KC", "Deshon Singleton": "KC",
    # LAC
    "Avery Smith": "LAC", "Jerand Bradley": "LAC", "Isaiah World": "LAC",
    "Greg Desrosiers": "LAC", "Sincere Brown": "LAC", "Lander Barton": "LAC",
    "Noah Avinger": "LAC", "Jahmeer Carter": "LAC", "Nadame Tucker": "LAC",
    # LAR
    "Matthew Caldwell": "LAR", "Eddie Walls": "LAR", "Austin Blaske": "LAR",
    "Darryl Peterson": "LAR", "Dan Villari": "LAR", "Nikhai Hill-Green": "LAR",
    "Dean Connors": "LAR", "Jaxson Moi": "LAR",
    # LV
    "Gary Smith III": "LV", "Roman Hemby": "LV", "Jacob Clark": "LV",
    "Sawyer Robertson": "LV", "Caleb Offord": "LV",
    # MIA
    "Anthony Hankerson": "MIA", "Mark Gronowski": "MIA", "Mason Reiger": "MIA",
    "Rene Konga": "MIA", "Le'Veon Moss": "MIA", "Louis Moore": "MIA",
    "Donaven McCulley": "MIA",
    # MIN
    "Tristan Leigh": "MIN", "Tristian Leigh": "MIN", "Dillon Bell": "MIN",
    "Brett Thorson": "MIN", "Scooby Williams": "MIN", "Marcus Allen": "MIN",
    "Da'Veawn Armstead": "MIN", "Jordan Botelho": "MIN", "Tyreek Chappell": "MIN",
    "Monkell Goodwine": "MIN", "Shaleak Knotts": "MIN", "Keli Lawson": "MIN",
    "Delby Lemieux": "MIN", "Marcus Sanders Jr.": "MIN", "Cam'Ron Stewart": "MIN",
    "Jacob Thomas": "MIN", "Arden Walker": "MIN", "Kejon Owens": "MIN",
    "Tomas Rimac": "MIN", "Luke Wysong": "MIN",
    # NE
    "Tanner Arkin": "NE", "David Blay": "NE", "Channing Canada": "NE",
    "Nick DeGennaro": "NE", "Kyle Dixon": "NE", "Cameron Dorner": "NE",
    "Kenneth Harris": "NE", "Jimmy Kibble": "NE", "Myles Montgomery": "NE",
    "JonDarius Morgan": "NE", "Jacob Rizy": "NE",
    # NO
    "Alex Wollschlaeger": "NO", "Jeremiah McClendon": "NO", "Cody Hardy": "NO",
    "Alan Herron": "NO", "Michael Heldman": "NO", "Keeshawn Silver": "NO",
    "Dashawn Jones": "NO", "Mason Shipley": "NO",
    # NYG
    "Thaddeus Dixon": "NYG", "Ben Mann": "NYG", "Anquin Barnes": "NYG",
    "Dominic Zvada": "NYG", "Damon Bankston": "NYG",
    # NYJ
    "Caullin Lacy": "NYJ", "Caulin Lacy": "NYJ", "Garrison Grimes": "NYJ",
    "Will Ferrin": "NYJ", "Kendrick Blackshire": "NYJ", "Chip Trayanum": "NYJ",
    "Chase Curtis": "NYJ", "Mory Bamba": "NYJ", "Sam Scott": "NYJ",
    # PHI
    "Dae'Quan Wright": "PHI", "Deontae Lawson": "PHI", "Joshua Weru": "PHI",
    # PIT
    "Lake McRee": "PIT",
    # SEA
    "Devean Deal": "SEA", "Lance Mason": "SEA", "Uso Seumalo": "SEA",
    "Michael Briscoe": "SEA",
    # SF
    "James Thompson": "SF", "Will Pauling": "SF", "Khalil Dinkins": "SF",
    "Mikail Kamara": "SF", "Jalen Stroman": "SF",
    # TB
    "Jalon Daniels": "TB", "Eric Rivers": "TB", "Deshawn McKnight": "TB",
    "Jack Pyburn": "TB", "Aidan Laros": "TB",
    # TEN
    "Tyren Montgomery": "TEN", "Latrell McCutchin Sr.": "TEN",
    "Latrell McCutchin": "TEN", "Jalen McMurray": "TEN", "Shad Banks": "TEN",
    "Aamil Wagner": "TEN", "Mani Powell": "TEN",
    # WSH
    "Fred Davis II": "WSH", "Quentin Moore": "WSH", "Jeffrey M'ba": "WSH",
    "Jaden Bradley": "WSH", "Robert Henry Jr.": "WSH", "Malik Spencer": "WSH",
    "Tanoa Togiai": "WSH",
}

udfa_map = {_norm_name(k): v for k, v in UDFA_MAP_RAW.items()}

# Players predicted mock R5-7 who actually went undrafted
MOCK_TO_UNDRAFTED = {
    "David Gusta", "Haynes King", "Sawyer Robertson", "Dan Villari",
    "Mason Reiger", "DJ Rogers", "Jeff Caldwell", "Luke Altmyer",
    "Fa'alili Fa'amoe", "J'Mari Taylor", "Diego Pounds", "Bryson Eason",
    "Cameron Ball", "Vincent Anthony Jr.", "Bishop Fitzgerald", "Le'Veon Moss",
    "Joey Aguilar", "Roman Hemby", "Michael Trigg", "Jaeden Roberts",
    "Dontay Corleone", "Tyreak Sapp", "Logan Fano", "Louis Moore",
}

for fname in ('prospects_2026.json', 'prospects.json'):
    path = os.path.join(DATA_DIR, fname)
    d = json.load(open(path))
    mock_cleared = 0
    udfa_assigned = 0

    for p in d['prospects']:
        # Step 1: clear mock draft round for players who went undrafted
        if p['name'] in MOCK_TO_UNDRAFTED and p.get('round_source') == 'mock':
            p['draft_round'] = None
            p['draft_pick']  = None
            p['round_source'] = None
            p['team'] = None
            mock_cleared += 1

        # Step 2: assign UDFA team for undrafted players
        if not p.get('draft_round'):
            team = udfa_map.get(_norm_name(p['name']))
            if team:
                p['team'] = team
                udfa_assigned += 1

    with open(path, 'w') as f:
        json.dump(d, f, indent=2)
    print(f'{fname}: cleared {mock_cleared} mock picks, assigned {udfa_assigned} UDFA teams')
