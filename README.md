# Footy Career Sim — V6 Career Calendar & Economy

A local Flask + SQLite football career simulator for macOS.

## V6 playable loop

- A persistent 52-week July–June calendar
- Pre-season, club season, international windows, free weeks and close season
- Domestic league rounds scheduled around international windows
- Double-match weeks for long lower-division calendars
- National-team selection, qualifiers, Nations League windows and summer finals cycles
- Free recovery/training weeks when the player is not selected internationally
- Sealed match sessions and evidence-based full-time reports
- Season closure separated from the offseason and next-season rollover
- A broad transfer market with formal offers, monitoring interest, squad roles and contracts
- Weekly salary, agent commission, tax reserve and living costs
- Endorsements, virtual investment funds, property and optional virtual wagering
- Football-focused offseason programmes: recovery, holiday, individual camp, commercial, charity and agent work

## World foundation

The V5 database remains intact:

- 16 countries
- 21 leagues
- 390 real-name club identities
- Top two divisions in England, Spain, Italy, Germany and France
- Promotion, relegation, continental qualification and background honours

## Honest boundaries

Domestic cups and continental competitions are visible on the master calendar and continue to generate background honours/qualification records. Full playable cup brackets, detailed international qualifying tables and live national-team match replays remain separate future engines.

Investment prices and virtual wagers are fictional gameplay systems using career currency only.

## Start

```bash
./start.sh
```

Open the local address printed by Flask. This project should remain bound to `127.0.0.1`.

## Test

```bash
source .venv/bin/activate
python -m pytest -q
```
