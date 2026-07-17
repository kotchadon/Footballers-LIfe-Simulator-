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
