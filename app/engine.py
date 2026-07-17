from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class MatchResult:
    home_goals: int
    away_goals: int


def poisson(lam: float, rng: random.Random) -> int:
    """Generate a small Poisson-distributed score without external packages."""
    limit = math.exp(-lam)
    product = 1.0
    count = 0
    while product > limit:
        count += 1
        product *= rng.random()
    return max(0, count - 1)


def simulate_score(home_strength: int, away_strength: int, rng=None) -> MatchResult:
    rng = rng or random.Random()
    difference = home_strength - away_strength
    home_xg = max(0.35, min(3.2, 1.35 + difference / 35 + 0.22))
    away_xg = max(0.25, min(2.9, 1.15 - difference / 40))
    return MatchResult(poisson(home_xg, rng), poisson(away_xg, rng))


def player_selection_probability(overall: int, club_strength: int, fitness: int, morale: int) -> float:
    score = 0.52 + (overall - club_strength) * 0.025
    score += (fitness - 75) * 0.006
    score += (morale - 60) * 0.003
    return max(0.08, min(0.98, score))


def simulate_player_performance(
    *,
    player_name: str,
    position: str,
    overall: int,
    fitness: int,
    morale: int,
    team_goals: int,
    opponent_goals: int,
    rng=None,
):
    rng = rng or random.Random()
    attacking_weight = {
        "ST": 1.0,
        "LW": 0.86,
        "RW": 0.86,
        "CAM": 0.75,
        "CM": 0.48,
        "CDM": 0.23,
        "LB": 0.18,
        "RB": 0.18,
        "CB": 0.10,
        "GK": 0.01,
    }.get(position, 0.5)

    involvement = max(0.05, min(0.78, 0.15 + attacking_weight * 0.25 + (overall - 50) / 180))
    goals = sum(1 for _ in range(team_goals) if rng.random() < involvement * attacking_weight)
    remaining_goals = max(0, team_goals - goals)
    assists = sum(1 for _ in range(remaining_goals) if rng.random() < involvement * 0.72)

    rating = 6.05
    rating += goals * 1.05 + assists * 0.62
    rating += (fitness - 75) / 100
    rating += (morale - 60) / 150
    rating += rng.uniform(-0.55, 0.55)
    if team_goals > opponent_goals:
        rating += 0.22
    elif team_goals < opponent_goals:
        rating -= 0.20
    rating = round(max(3.5, min(10.0, rating)), 1)

    motm = rating >= 8.4 or (goals >= 2 and rating >= 7.7)
    commentary = build_commentary(player_name, goals, assists, rating, team_goals, opponent_goals, rng)
    return {
        "goals": goals,
        "assists": assists,
        "rating": rating,
        "motm": motm,
        "commentary": commentary,
    }


def build_commentary(player_name, goals, assists, rating, team_goals, opponent_goals, rng):
    events = [
        "08' — Both sides settle into the match.",
        "21' — The midfield battle becomes increasingly physical.",
        "39' — A dangerous attack is stopped at the edge of the box.",
        "58' — The manager asks the team to play with more urgency.",
        "76' — Tired legs begin to create spaces between the lines.",
    ]
    for _ in range(goals):
        minute = rng.randint(12, 88)
        events.append(f"{minute:02d}' — GOAL! {player_name} finishes the chance brilliantly.")
    for _ in range(assists):
        minute = rng.randint(12, 88)
        events.append(f"{minute:02d}' — {player_name} creates the goal with a decisive final pass.")
    events.append(f"90' — Full time. Player rating: {rating:.1f}.")
    return "\n".join(sorted(events, key=lambda line: int(line.split("'")[0])))
