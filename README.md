# Footballer's Life Simulator

**A browser-based football career simulation built with Python, Flask and SQLite.**

Most football career games revolve around the next match. I wanted to build something that paid attention to everything between matches as well: training, selection, transfers, injuries, money, international call-ups and the decisions that shape a player's career over several seasons.

Footballer's Life Simulator is a personal project that brings those pieces together in one persistent career. You create a player, work through a football calendar, develop your abilities and deal with the consequences of what happens on and off the pitch.

## More than a match simulator

The game follows a **52-week July–June calendar**, rather than treating a season as a simple list of fixtures. Club matches have to fit around pre-season, international breaks, transfer windows, recovery periods and the offseason. Longer lower-division schedules can include double-match weeks.

Your player develops over time through position-specific attributes, training, match performances and career decisions. Form, fitness, injuries, suspensions and selection opportunities influence the journey. Matches have their own sessions and post-match reports, so a result becomes part of the player's history rather than disappearing after the final whistle.

There is also an off-pitch side. Contracts, club interest and formal transfer offers sit alongside wages, agent fees, living expenses and a financial history. Endorsements, property and fictional investments add decisions that have little to do with scoring goals but still matter to the wider career.

## A football world that continues around you

The underlying game world currently contains **16 countries, 21 leagues and 390 club identities**, including the top two divisions in England, Spain, Italy, Germany and France.

Domestic league tables, promotion and relegation, continental qualification and background competition honours give the world continuity across seasons. A player can move clubs, look back at previous seasons and see how their career fits into that wider football landscape.

International football is part of the calendar too, with national-team selection, qualifying windows, Nations League periods and major tournament cycles. Not being selected can be meaningful as well: it leaves time for training or recovery while other players are away.

## The development side

I built this as a **stateful simulation**, not a collection of disconnected screens. A decision in one week can change what is available weeks later, and the game needs to remember it when a season ends.

Under the hood:

- **Python and Flask** handle the application, career logic and game actions.
- **SQLite** stores careers, player attributes, fixtures, standings, contracts, finances, match records and season history.
- **HTML, CSS and JavaScript** power the local browser interface, dashboards and match presentation.
- Separate systems manage the world calendar, player progression, match outcomes, transfer activity, international football and the simulated economy.
- Database migrations help preserve older career saves as new features are added.

The work has involved both game design and backend engineering: getting the rules of a football season to fit together, maintaining consistency across many kinds of state and making the interface show the right information at the right point in a career.

## Current stage

The project is at its **V6 career-calendar and economy stage**. The club-season career loop, finances, transfers, international-calendar activity and historical records are implemented, but the simulation is still being expanded.

Some competitions exist as calendar events or background outcomes rather than full playable tournaments. In particular, complete domestic-cup and continental knockout brackets, detailed international qualifying tables and live national-team match replays are not yet separate playable engines.

This is an independent fan-made simulation, not an official football game. Club identities are used for the simulated world; real-world football organisations are not affiliated with the project. Financial markets, investments and optional virtual wagering use **fictional in-game currency only**.

## Why I built it

I'm a football fan, and I wanted the career itself to feel like the game. Winning a match should matter, but so should being dropped from the starting XI, getting a transfer offer, managing an injury or deciding how to spend a quiet week.

From a development perspective, the interesting challenge has been building systems that affect one another without losing the continuity of the career. That's still what I'm working on as the simulator grows.
