# Footy Career Sim

A local, menu-driven football career simulator built with Flask and SQLite.

## Current playable loop

- Create a 16-year-old player
- Join a fictional starting club
- Play a double round-robin league season
- Simulate every matchweek
- Manager selection based on overall, club strength, fitness and morale
- Track goals, assists, ratings, wins, draws, losses and Player of the Match awards
- Persistent SQLite save

## Run locally

```bash
source .venv/bin/activate
python run.py
```

Open <http://127.0.0.1:5000>.

## Run tests

```bash
pytest -q
```

## Immediate roadmap

1. Season rollover and player aging
2. Contracts and transfer offers
3. Multiple countries and divisions
4. Domestic cup and continental qualification
5. Injuries, cards and suspensions
6. Detailed player attributes and position-weighted overall
7. Club history and competition-separated career statistics
8. Awards, reputation, wages, equipment and loans

## Architecture

- `app/engine.py` — pure match and player-performance simulation
- `app/services.py` — careers, fixtures, standings and persistence
- `app/routes.py` — web routes
- `app/schema.sql` — SQLite schema
- `app/templates/` — local interface

## Helper scripts

```bash
./start.sh       # create environment if needed and run the game
./reset_save.sh  # delete the local career save
```

## V4 — Sealed Match Integrity

The match centre uses a two-phase lifecycle:

1. **Prepare:** generate one immutable simulation snapshot and event ledger without changing career state.
2. **Complete:** commit fixtures, standings, statistics, XP, money, cards, injuries and week advancement exactly once at full time or Skip.

The browser never receives the final score or post-match report in the initial HTML. Events are revealed sequentially through an API. The final report is evidence-based: its strengths, gaps, turning points and coaching recommendations are derived from the stored event ledger and metric snapshot.

Important modules:

- `app/engine.py` — event ledger, player metrics and post-match analyst.
- `app/services.py` — sealed match sessions and transactional/idempotent completion.
- `app/routes.py` — refresh-safe match URLs and replay APIs.
- `tests/test_match_integrity.py` — spoiler, sequencing, idempotency and traceability tests.

