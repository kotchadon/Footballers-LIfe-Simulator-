# Footy Career Sim V2

A local, menu-driven football career simulator built with Flask and SQLite.

## V2 playable systems

- Create a 16-year-old footballer in any major position
- Position-weighted attributes and overall rating
- Weekly training or recovery decisions
- Starting XI, substitute, bench, injury and suspension selection states
- Goals, assists, minutes, cards, match ratings and MOTM awards
- Injuries, yellow-card accumulation and red-card suspensions
- Wages, match bonuses, season prize money and financial history
- Double round-robin league simulation
- Season rollover, aging, awards and persistent season history
- Performance-based transfer offers, signing bonuses and club history
- Existing V1 saves migrate automatically

## Run locally

```bash
./start.sh
```

Open <http://127.0.0.1:5000>.

## Run tests

```bash
source .venv/bin/activate
python -m pytest -q
```

## Next roadmap

1. Multiple countries, leagues and divisions driven by JSON data
2. Domestic cups and continental competitions
3. Full squads and position competition inside every club
4. Contracts, agents, negotiations and transfer fees
5. National teams, qualification and World Cup
6. More detailed attributes, personalities and manager tactics
7. Equipment, endorsements, investments, loans and lifestyle events
8. Faster multi-week simulation and richer news commentary
