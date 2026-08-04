# Footy Career Sim

A local, menu-driven football career simulator built with Flask and SQLite.

## V5 — Football World Architecture

The game now uses a data-driven world rather than one hardcoded fictional league.

### Launch world

- 16 countries
- 21 real-name leagues
- 390 real club identities
- The top two divisions of England, Spain, Italy, Germany and France
- Additional leagues in Portugal, the Netherlands, Scotland, Ireland, the United States/Canada, Brazil, Argentina, Saudi Arabia, Japan, Australia and India
- League and club reputation
- Youth and reserve-unit ratings for every club
- Career-specific league memberships
- Promotion and relegation between the paired top-five divisions
- Cross-country transfer offers
- Continental qualification records
- Persistent competition honours
- Player of the Match, Player of the Month, season awards and a Ballon d'Or-style award

Real player databases are deliberately not included. Club strength and reputation values are gameplay balance ratings, not official rankings.

### Honest competition status

Domestic cups, super cups, continental club competitions and major international tournaments exist as real-name competition entities. League qualification and background honours are recorded now. Full playable cup draws, knockout fixtures, national-team selection and international calendars are later engines; the interface labels that distinction rather than pretending every trophy is already playable.

## Match integrity

The match centre uses a two-phase lifecycle:

1. **Prepare:** generate one sealed simulation and event ledger without changing career state.
2. **Complete:** commit fixtures, standings, statistics, XP, money, cards, injuries and week advancement exactly once at full time or Skip.

The initial HTML does not contain the final report. The report is assembled after full time from the same completed statistical snapshot and event ledger.

## Run locally

```bash
./start.sh
```

Open the local URL printed by Flask. This project is intended to bind only to `127.0.0.1`.

## Run tests

```bash
source .venv/bin/activate
python -m pytest -q
```

## Architecture

- `app/world_data.py` — normalized league, club and competition seed data
- `app/world.py` — memberships, promotion/relegation, world simulation, qualification and awards
- `app/engine.py` — match and player-performance simulation
- `app/services.py` — career orchestration, sealed matches, transfers and transactions
- `app/db.py` / `app/schema.sql` — migrations and SQLite schema
- `app/routes.py` — web/API routes
- `app/templates/` — local interface

## Current playable loop

1. Create a 16-year-old player.
2. Nationality influences a believable starting market; top-five prospects begin in the second tier.
3. Play an active league season while the rest of the football world resolves efficiently in the background.
4. Build attributes, manager trust, reputation and awards.
5. Finish the season, process promotion/relegation and continental qualification, then consider cross-league transfer offers.
