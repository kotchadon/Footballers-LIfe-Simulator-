from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class MatchResult:
    home_goals: int
    away_goals: int


POSITION_WEIGHTS = {
    "ST": {"pace": 0.18, "shooting": 0.34, "passing": 0.10, "dribbling": 0.18, "defending": 0.02, "physical": 0.18},
    "LW": {"pace": 0.25, "shooting": 0.20, "passing": 0.16, "dribbling": 0.25, "defending": 0.03, "physical": 0.11},
    "RW": {"pace": 0.25, "shooting": 0.20, "passing": 0.16, "dribbling": 0.25, "defending": 0.03, "physical": 0.11},
    "CAM": {"pace": 0.11, "shooting": 0.18, "passing": 0.28, "dribbling": 0.26, "defending": 0.04, "physical": 0.13},
    "CM": {"pace": 0.09, "shooting": 0.11, "passing": 0.29, "dribbling": 0.19, "defending": 0.14, "physical": 0.18},
    "CDM": {"pace": 0.08, "shooting": 0.05, "passing": 0.21, "dribbling": 0.10, "defending": 0.30, "physical": 0.26},
    "LB": {"pace": 0.20, "shooting": 0.04, "passing": 0.16, "dribbling": 0.12, "defending": 0.27, "physical": 0.21},
    "RB": {"pace": 0.20, "shooting": 0.04, "passing": 0.16, "dribbling": 0.12, "defending": 0.27, "physical": 0.21},
    "CB": {"pace": 0.10, "shooting": 0.02, "passing": 0.10, "dribbling": 0.04, "defending": 0.40, "physical": 0.34},
    "GK": {"pace": 0.04, "shooting": 0.01, "passing": 0.13, "dribbling": 0.03, "defending": 0.43, "physical": 0.36},
}

ATTACKING_WEIGHT = {
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
}


def poisson(lam: float, rng: random.Random) -> int:
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


def create_starting_attributes(position: str, rng=None) -> dict[str, int]:
    rng = rng or random.Random()
    weights = POSITION_WEIGHTS.get(position, POSITION_WEIGHTS["CM"])
    attributes = {}
    for name, weight in weights.items():
        positional_bonus = round(weight * 26)
        attributes[name] = max(38, min(68, 43 + positional_bonus + rng.randint(-3, 3)))
    return attributes


def calculate_overall(attributes: dict[str, int], position: str, potential: int = 99) -> int:
    weights = POSITION_WEIGHTS.get(position, POSITION_WEIGHTS["CM"])
    value = sum(attributes[name] * weight for name, weight in weights.items())
    return min(potential, max(1, round(value)))


def player_selection_probability(overall: int, club_strength: int, fitness: int, morale: int) -> float:
    score = 0.52 + (overall - club_strength) * 0.025
    score += (fitness - 75) * 0.006
    score += (morale - 60) * 0.003
    return max(0.08, min(0.98, score))


def _event(minute: int, text: str, kind: str = "moment") -> dict[str, int | str]:
    return {"minute": minute, "text": text, "kind": kind}


def _minute(rng: random.Random, low: int, high: int, used: set[int]) -> int:
    low = max(1, low)
    high = min(89, max(low, high))
    candidates = [value for value in range(low, high + 1) if value not in used]
    minute = rng.choice(candidates) if candidates else rng.randint(low, high)
    used.add(minute)
    return minute


def build_commentary_events(
    player_name,
    goals,
    assists,
    rating,
    team_goals,
    opponent_goals,
    selection_status,
    minutes,
    yellow_cards,
    red_cards,
    injured,
    rng,
):
    """Build a score-consistent timeline for the browser match centre."""
    used: set[int] = {0, 90}
    start_minute = max(1, 90 - minutes)
    events = [_event(0, "Kick-off. The crowd rises as both teams settle into shape.", "kickoff")]

    if selection_status == "substitute":
        entrance = max(46, 90 - minutes)
        used.add(entrance)
        events.append(_event(entrance, f"{player_name} comes off the bench with instructions to attack the space.", "player"))

    generic_moments = [
        "A quick passing move pulls the defensive line out of position.",
        "The goalkeeper reacts sharply and pushes a driven effort away.",
        "A dangerous counterattack is stopped by a perfectly timed challenge.",
        "The midfield press forces a rushed clearance into the stands.",
        "A curling cross flashes through the six-yard box without a final touch.",
        "A long-range effort whistles narrowly past the post.",
        "The tempo rises as both sides begin committing more players forward.",
        "A corner causes chaos before the defence finally clears its lines.",
        "The manager demands a higher defensive line from the technical area.",
        "A clever one-two opens a shooting lane at the edge of the area.",
    ]
    for text in rng.sample(generic_moments, k=7):
        events.append(_event(_minute(rng, 5, 84, used), text, "chance"))

    player_goal_minutes = []
    for _ in range(goals):
        minute = _minute(rng, max(6, start_minute), 87, used)
        player_goal_minutes.append(minute)
        events.append(_event(minute, f"GOAL! {player_name} attacks the opening and finishes with conviction.", "goal_for"))

    assisted_goals = min(assists, max(0, team_goals - goals))
    for _ in range(assisted_goals):
        minute = _minute(rng, max(6, start_minute), 87, used)
        events.append(_event(minute, f"GOAL! {player_name} supplies the decisive pass and a teammate converts.", "goal_for"))

    remaining_team_goals = max(0, team_goals - goals - assisted_goals)
    for _ in range(remaining_team_goals):
        minute = _minute(rng, 4, 88, used)
        events.append(_event(minute, "GOAL! Your side completes a sharp move with a composed finish.", "goal_for"))

    for _ in range(opponent_goals):
        minute = _minute(rng, 4, 88, used)
        events.append(_event(minute, "GOAL AGAINST. The opposition punish a gap and find the net.", "goal_against"))

    if yellow_cards:
        events.append(_event(_minute(rng, max(12, start_minute), 82, used), f"Yellow card for {player_name} after a late challenge.", "card"))
    if red_cards:
        events.append(_event(_minute(rng, max(38, start_minute), 86, used), f"RED CARD! {player_name} is dismissed and the game changes immediately.", "card"))
    if injured:
        events.append(_event(_minute(rng, max(20, start_minute), 84, used), f"{player_name} stays down after an awkward collision and receives treatment.", "injury"))

    events.append(_event(90, f"Full time. {player_name}'s match rating: {rating:.1f}.", "full_time"))
    return sorted(events, key=lambda item: (int(item["minute"]), item["kind"]))


def commentary_to_text(events: list[dict[str, int | str]]) -> str:
    return "\n".join(f"{int(event['minute']):02d}' — {event['text']}" for event in events)


def simulate_player_performance(
    *,
    player_name: str,
    position: str,
    overall: int,
    fitness: int,
    morale: int,
    team_goals: int,
    opponent_goals: int,
    minutes: int = 90,
    selection_status: str = "starter",
    physical: int = 50,
    defending: int = 50,
    rng=None,
):
    rng = rng or random.Random()
    attacking_weight = ATTACKING_WEIGHT.get(position, 0.5)
    minutes_factor = max(0.15, min(1.0, minutes / 90))
    involvement = max(
        0.03,
        min(0.78, (0.15 + attacking_weight * 0.25 + (overall - 50) / 180) * minutes_factor),
    )

    goals = sum(1 for _ in range(team_goals) if rng.random() < involvement * attacking_weight)
    remaining_goals = max(0, team_goals - goals)
    assists = sum(1 for _ in range(remaining_goals) if rng.random() < involvement * 0.72)

    card_weight = 0.025 + max(0, defending - 50) / 900
    if position in {"CB", "CDM", "LB", "RB"}:
        card_weight += 0.025
    yellow_cards = int(rng.random() < card_weight * minutes_factor)
    red_cards = int(yellow_cards and rng.random() < 0.045)

    injury_chance = 0.010 + max(0, 68 - fitness) * 0.0011 - max(0, physical - 50) * 0.00018
    injured = rng.random() < max(0.003, injury_chance) * minutes_factor
    injury_weeks = rng.randint(1, 5) if injured else 0

    rating = 6.0
    rating += goals * 1.05 + assists * 0.62
    rating += (fitness - 75) / 125
    rating += (morale - 60) / 160
    rating += rng.uniform(-0.55, 0.55)
    if selection_status == "substitute":
        rating += 0.08
    if team_goals > opponent_goals:
        rating += 0.22
    elif team_goals < opponent_goals:
        rating -= 0.20
    rating -= yellow_cards * 0.22 + red_cards * 1.35
    if injured:
        rating -= 0.18
    rating = round(max(3.5, min(10.0, rating)), 1)

    motm = rating >= 8.4 or (goals >= 2 and rating >= 7.7)
    events = build_commentary_events(
        player_name,
        goals,
        assists,
        rating,
        team_goals,
        opponent_goals,
        selection_status,
        minutes,
        yellow_cards,
        red_cards,
        injured,
        rng,
    )
    return {
        "goals": goals,
        "assists": assists,
        "yellow_cards": yellow_cards,
        "red_cards": red_cards,
        "injured": injured,
        "injury_weeks": injury_weeks,
        "rating": rating,
        "motm": motm,
        "events": events,
        "commentary": commentary_to_text(events),
    }


def build_commentary(
    player_name,
    goals,
    assists,
    rating,
    team_goals,
    opponent_goals,
    selection_status,
    minutes,
    yellow_cards,
    red_cards,
    injured,
    rng,
):
    """Backward-compatible text wrapper retained for tests and saved reports."""
    return commentary_to_text(
        build_commentary_events(
            player_name,
            goals,
            assists,
            rating,
            team_goals,
            opponent_goals,
            selection_status,
            minutes,
            yellow_cards,
            red_cards,
            injured,
            rng,
        )
    )

