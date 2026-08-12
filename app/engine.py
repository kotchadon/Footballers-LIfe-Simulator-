from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any


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

DEFENSIVE_WEIGHT = {
    "ST": 0.08,
    "LW": 0.16,
    "RW": 0.16,
    "CAM": 0.22,
    "CM": 0.55,
    "CDM": 0.92,
    "LB": 0.84,
    "RB": 0.84,
    "CB": 1.0,
    "GK": 0.30,
}

CREATIVE_WEIGHT = {
    "ST": 0.35,
    "LW": 0.72,
    "RW": 0.72,
    "CAM": 1.0,
    "CM": 0.88,
    "CDM": 0.58,
    "LB": 0.52,
    "RB": 0.52,
    "CB": 0.22,
    "GK": 0.08,
}


# ---------------------------------------------------------------------------
# Core probability helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Authoritative match event model
# ---------------------------------------------------------------------------

def _event(minute: int, text: str, kind: str = "moment", **metadata: Any) -> dict[str, Any]:
    return {
        "minute": int(minute),
        "text": text,
        "kind": kind,
        "metadata": metadata,
    }


def _minute(rng: random.Random, low: int, high: int, used: set[int]) -> int:
    low = max(1, low)
    high = min(89, max(low, high))
    candidates = [value for value in range(low, high + 1) if value not in used]
    minute = rng.choice(candidates) if candidates else rng.randint(low, high)
    used.add(minute)
    return minute


def _bounded_round(value: float, low: int, high: int) -> int:
    return max(low, min(high, round(value)))


def _simulate_player_metrics(
    *,
    position: str,
    overall: int,
    fitness: int,
    minutes: int,
    goals: int,
    assists: int,
    physical: int,
    defending: int,
    rng: random.Random,
) -> dict[str, Any]:
    """Generate a coherent statistical line used by both commentary and analysis.

    Every downstream report is derived from this immutable metric snapshot. Nothing
    in the post-match report is independently randomised.
    """
    factor = max(0.0, min(1.0, minutes / 90))
    attack = ATTACKING_WEIGHT.get(position, 0.5)
    creative = CREATIVE_WEIGHT.get(position, 0.5)
    defensive = DEFENSIVE_WEIGHT.get(position, 0.4)
    quality = max(0.55, min(1.35, overall / 65))

    shots = max(goals, _bounded_round((0.6 + attack * 3.2) * factor * quality + rng.uniform(-0.5, 1.2), 0, 9))
    shots_on_target = min(shots, max(goals, _bounded_round(shots * rng.uniform(0.38, 0.72), 0, shots)))
    xg = round(max(goals * 0.12, shots * rng.uniform(0.12, 0.34) + goals * rng.uniform(0.05, 0.22)), 2)

    key_passes = max(assists, _bounded_round((0.4 + creative * 2.6) * factor * quality + rng.uniform(-0.5, 0.8), 0, 7))
    big_chances_created = min(key_passes, max(assists, _bounded_round(key_passes * rng.uniform(0.18, 0.52), 0, 4)))
    xa = round(max(assists * 0.08, key_passes * rng.uniform(0.08, 0.24)), 2)

    pass_base = {
        "GK": 28, "CB": 52, "LB": 43, "RB": 43, "CDM": 55,
        "CM": 58, "CAM": 48, "LW": 36, "RW": 36, "ST": 27,
    }.get(position, 42)
    passes_attempted = _bounded_round(pass_base * factor * rng.uniform(0.82, 1.18), 0, 95)
    accuracy_target = max(0.55, min(0.95, 0.69 + (overall - 50) * 0.004 + rng.uniform(-0.07, 0.06)))
    passes_completed = min(passes_attempted, _bounded_round(passes_attempted * accuracy_target, 0, passes_attempted))

    dribble_attempts = _bounded_round((0.2 + attack * 3.0 + creative * 1.2) * factor + rng.uniform(-0.6, 1.1), 0, 9)
    dribbles_completed = min(
        dribble_attempts,
        _bounded_round(dribble_attempts * max(0.25, min(0.82, 0.46 + (overall - 55) * 0.006 + rng.uniform(-0.12, 0.12))), 0, dribble_attempts),
    )

    tackle_attempts = _bounded_round((0.3 + defensive * 4.3) * factor + rng.uniform(-0.6, 1.0), 0, 10)
    tackles_won = min(
        tackle_attempts,
        _bounded_round(tackle_attempts * max(0.30, min(0.90, 0.52 + (defending - 50) * 0.006 + rng.uniform(-0.10, 0.12))), 0, tackle_attempts),
    )

    duels = _bounded_round((2.0 + attack * 2.2 + defensive * 2.6) * factor + rng.uniform(-0.8, 1.8), 0, 15)
    duel_rate = max(0.25, min(0.82, 0.46 + (physical - 50) * 0.006 + rng.uniform(-0.12, 0.12)))
    duels_won = min(duels, _bounded_round(duels * duel_rate, 0, duels))

    touches = _bounded_round((passes_attempted * 1.22 + shots * 2 + dribble_attempts * 2.4 + tackle_attempts) * rng.uniform(0.90, 1.10), 0, 130)
    turnovers = _bounded_round((touches * rng.uniform(0.035, 0.095)) + max(0, dribble_attempts - dribbles_completed) * 0.7, 0, 16)
    fouls_committed = _bounded_round((0.2 + defensive * 1.5) * factor + rng.uniform(-0.4, 0.8), 0, 5)
    progressive_actions = _bounded_round((key_passes + dribbles_completed + passes_completed * 0.08) * rng.uniform(0.75, 1.15), 0, 18)

    pass_accuracy = round((passes_completed / passes_attempted * 100), 1) if passes_attempted else 0.0
    shot_accuracy = round((shots_on_target / shots * 100), 1) if shots else 0.0
    duel_win_rate = round((duels_won / duels * 100), 1) if duels else 0.0
    tackle_success = round((tackles_won / tackle_attempts * 100), 1) if tackle_attempts else 0.0
    dribble_success = round((dribbles_completed / dribble_attempts * 100), 1) if dribble_attempts else 0.0

    return {
        "shots": shots,
        "shots_on_target": shots_on_target,
        "shot_accuracy": shot_accuracy,
        "xg": xg,
        "key_passes": key_passes,
        "big_chances_created": big_chances_created,
        "xa": xa,
        "passes_attempted": passes_attempted,
        "passes_completed": passes_completed,
        "pass_accuracy": pass_accuracy,
        "dribbles_attempted": dribble_attempts,
        "dribbles_completed": dribbles_completed,
        "dribble_success": dribble_success,
        "tackles_attempted": tackle_attempts,
        "tackles_won": tackles_won,
        "tackle_success": tackle_success,
        "duels": duels,
        "duels_won": duels_won,
        "duel_win_rate": duel_win_rate,
        "touches": touches,
        "turnovers": turnovers,
        "fouls_committed": fouls_committed,
        "progressive_actions": progressive_actions,
        "schema_version": 1,
    }


def _rating_from_metrics(
    *,
    metrics: dict[str, Any],
    goals: int,
    assists: int,
    yellow_cards: int,
    red_cards: int,
    injured: bool,
    fitness: int,
    morale: int,
    team_goals: int,
    opponent_goals: int,
    selection_status: str,
    rng: random.Random,
) -> float:
    rating = 5.85
    rating += goals * 1.02 + assists * 0.64
    rating += metrics["key_passes"] * 0.08
    rating += metrics["tackles_won"] * 0.045
    rating += metrics["dribbles_completed"] * 0.04
    rating += max(-0.35, min(0.28, (metrics["pass_accuracy"] - 75) / 60))
    rating += max(-0.30, min(0.22, (metrics["duel_win_rate"] - 50) / 80))
    rating -= metrics["turnovers"] * 0.035
    rating += (fitness - 75) / 140
    rating += (morale - 60) / 180
    rating += rng.uniform(-0.22, 0.22)
    if selection_status == "substitute":
        rating += 0.06
    if team_goals > opponent_goals:
        rating += 0.20
    elif team_goals < opponent_goals:
        rating -= 0.18
    rating -= yellow_cards * 0.22 + red_cards * 1.35
    if injured:
        rating -= 0.18
    return round(max(3.5, min(10.0, rating)), 1)


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
    metrics: dict[str, Any] | None = None,
):
    """Build a score-consistent, evidence-tagged event ledger.

    The event ledger is authoritative. The browser replays these events and the
    post-match analyst consumes the same events and metrics.
    """
    metrics = metrics or {}
    used: set[int] = {0, 90}
    start_minute = max(1, 90 - minutes)
    events: list[dict[str, Any]] = [
        _event(0, "Kick-off. Both sides settle into shape as the crowd raises the volume.", "kickoff", side="neutral")
    ]

    if selection_status == "substitute":
        entrance = max(46, 90 - minutes)
        used.add(entrance)
        events.append(_event(entrance, f"{player_name} comes off the bench with instructions to attack the space.", "player_on", side="player"))

    generic_moments = [
        ("A quick passing move pulls the defensive line out of position.", "chance", "neutral"),
        ("The goalkeeper reacts sharply and pushes a driven effort away.", "save", "neutral"),
        ("A dangerous counterattack is stopped by a perfectly timed challenge.", "defensive_action", "neutral"),
        ("The midfield press forces a rushed clearance into the stands.", "press", "neutral"),
        ("A curling cross flashes through the six-yard box without a final touch.", "chance", "neutral"),
        ("A long-range effort whistles narrowly past the post.", "shot", "neutral"),
        ("The tempo rises as both sides commit more players forward.", "momentum", "neutral"),
        ("A corner causes chaos before the defence finally clears its lines.", "set_piece", "neutral"),
        ("The manager demands a higher line from the technical area.", "tactical", "neutral"),
        ("A clever one-two opens a shooting lane at the edge of the area.", "chance", "neutral"),
    ]
    for text, kind, side in rng.sample(generic_moments, k=5):
        events.append(_event(_minute(rng, 5, 84, used), text, kind, side=side))

    for goal_index in range(goals):
        minute = _minute(rng, max(6, start_minute), 87, used)
        events.append(
            _event(
                minute,
                f"GOAL! {player_name} attacks the opening and finishes with conviction.",
                "goal_for",
                side="player",
                contribution="goal",
                player_goal_number=goal_index + 1,
            )
        )

    assisted_goals = min(assists, max(0, team_goals - goals))
    for assist_index in range(assisted_goals):
        minute = _minute(rng, max(6, start_minute), 87, used)
        events.append(
            _event(
                minute,
                f"GOAL! {player_name} supplies the decisive pass and a teammate converts.",
                "goal_for",
                side="player",
                contribution="assist",
                player_assist_number=assist_index + 1,
            )
        )

    remaining_team_goals = max(0, team_goals - goals - assisted_goals)
    for _ in range(remaining_team_goals):
        events.append(_event(_minute(rng, 4, 88, used), "GOAL! Your side completes a sharp move with a composed finish.", "goal_for", side="player", contribution="team"))

    for _ in range(opponent_goals):
        events.append(_event(_minute(rng, 4, 88, used), "GOAL AGAINST. The opposition punish a gap and find the net.", "goal_against", side="opponent"))

    non_goal_on_target = max(0, int(metrics.get("shots_on_target", 0)) - goals)
    if non_goal_on_target:
        events.append(
            _event(
                _minute(rng, max(7, start_minute), 86, used),
                f"{player_name} tests the goalkeeper, who gets down quickly to make the save.",
                "player_shot_saved",
                side="player",
                metric="shots_on_target",
            )
        )
    if int(metrics.get("shots", 0)) > int(metrics.get("shots_on_target", 0)):
        events.append(
            _event(
                _minute(rng, max(7, start_minute), 86, used),
                f"{player_name} finds space but sends the effort off target.",
                "player_shot_off_target",
                side="player",
                metric="shots",
            )
        )
    if int(metrics.get("key_passes", 0)) > assists:
        events.append(
            _event(
                _minute(rng, max(5, start_minute), 86, used),
                f"{player_name} splits the line with a clever pass, but the chance is not converted.",
                "player_key_pass",
                side="player",
                metric="key_passes",
            )
        )
    if int(metrics.get("dribbles_completed", 0)) >= 2:
        events.append(
            _event(
                _minute(rng, max(6, start_minute), 84, used),
                f"{player_name} beats a defender one-on-one and drives the team forward.",
                "player_dribble",
                side="player",
                metric="dribbles_completed",
            )
        )
    if int(metrics.get("tackles_won", 0)) >= 2:
        events.append(
            _event(
                _minute(rng, max(5, start_minute), 84, used),
                f"{player_name} reads the danger and wins possession with a clean challenge.",
                "player_tackle",
                side="player",
                metric="tackles_won",
            )
        )
    if int(metrics.get("turnovers", 0)) >= 7:
        events.append(
            _event(
                _minute(rng, max(8, start_minute), 84, used),
                f"{player_name} loses possession in a dangerous area and the opposition break quickly.",
                "player_turnover",
                side="opponent",
                metric="turnovers",
            )
        )

    if yellow_cards:
        events.append(_event(_minute(rng, max(12, start_minute), 82, used), f"Yellow card for {player_name} after a late challenge.", "yellow_card", side="player"))
    if red_cards:
        events.append(_event(_minute(rng, max(38, start_minute), 86, used), f"RED CARD! {player_name} is dismissed and the match changes immediately.", "red_card", side="player"))
    if injured:
        events.append(_event(_minute(rng, max(20, start_minute), 84, used), f"{player_name} stays down after an awkward collision and receives treatment.", "injury", side="player"))

    events.append(_event(90, "Full time. The referee ends the match.", "full_time", side="neutral"))
    events.sort(key=lambda item: (int(item["minute"]), item["kind"]))

    player_score = 0
    opponent_score = 0
    for sequence, event in enumerate(events):
        if event["kind"] == "goal_for":
            player_score += 1
        elif event["kind"] == "goal_against":
            opponent_score += 1
        event["sequence"] = sequence
        event["score"] = {"player": player_score, "opponent": opponent_score}

    if player_score != team_goals or opponent_score != opponent_goals:
        raise AssertionError("Event ledger score does not match simulated score")
    return events


def commentary_to_text(events: list[dict[str, Any]]) -> str:
    return "\n".join(f"{int(event['minute']):02d}' — {event['text']}" for event in events)


# ---------------------------------------------------------------------------
# Evidence-based post-match analyst
# ---------------------------------------------------------------------------

def _evidence(label: str, value: str, event_sequences: list[int] | None = None) -> dict[str, Any]:
    return {"label": label, "value": value, "event_sequences": event_sequences or []}


def _ranked_insight(score: float, title: str, detail: str, evidence: list[dict[str, Any]], focus: str | None = None) -> dict[str, Any]:
    item = {"score": round(float(score), 2), "title": title, "detail": detail, "evidence": evidence}
    if focus:
        item["focus"] = focus
    return item


def _score_from_ledger(events: list[dict[str, Any]]) -> tuple[int, int]:
    return (
        sum(event.get("kind") == "goal_for" for event in events),
        sum(event.get("kind") == "goal_against" for event in events),
    )


def build_post_match_analysis(
    *,
    player_name: str,
    position: str,
    selection_status: str,
    minutes: int,
    goals: int,
    assists: int,
    rating: float,
    motm: bool,
    yellow_cards: int,
    red_cards: int,
    injured: bool,
    team_goals: int,
    opponent_goals: int,
    metrics: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a deterministic report from the sealed event ledger and metrics.

    This function contains no randomness. It rejects inconsistent scorelines and
    ranks strengths/gaps by severity so the report explains the actual match.
    """
    ledger_team_goals, ledger_opponent_goals = _score_from_ledger(events)
    if (ledger_team_goals, ledger_opponent_goals) != (team_goals, opponent_goals):
        raise ValueError("Post-match report rejected: scoreline does not match the sealed event ledger")

    result_word = "win" if team_goals > opponent_goals else "draw" if team_goals == opponent_goals else "defeat"
    scoreline = f"{team_goals}–{opponent_goals}"
    goal_events = [event for event in events if event.get("kind") in {"goal_for", "goal_against"}]
    player_events = [
        event for event in events
        if event.get("metadata", {}).get("side") == "player"
        or event.get("kind") in {"yellow_card", "red_card", "injury"}
    ]

    if selection_status not in {"starter", "substitute"}:
        reason = {
            "injured": "unavailable through injury",
            "suspended": "unavailable through suspension",
            "bench": "an unused substitute",
        }.get(selection_status, "not selected")
        return {
            "schema_version": 2,
            "source": "sealed_event_ledger",
            "headline": f"No playing minutes in a {scoreline} {result_word}",
            "verdict": f"{player_name} was {reason}; the report therefore grades availability, not on-pitch performance.",
            "result_context": _describe_score_flow(goal_events, team_goals, opponent_goals, result_word, scoreline),
            "turning_points": [
                {"minute": event["minute"], "text": event["text"], "event_sequence": event["sequence"]}
                for event in goal_events[:5]
            ],
            "strengths": [],
            "gaps": [{
                "score": 100,
                "title": "No match evidence",
                "detail": "There were no playing minutes from which to assess technical strengths or weaknesses.",
                "evidence": [_evidence("Selection", selection_status)],
            }],
            "coaching_actions": [{
                "focus": "recovery" if selection_status == "injured" else "balanced",
                "title": "Return to availability",
                "detail": "Prioritise readiness and selection before making technical conclusions from this fixture.",
                "evidence": [_evidence("Minutes", "0")],
            }],
            "metrics": metrics,
            "trace": {
                "event_count": len(events),
                "source_event_sequences": [],
                "goals_from_events": ledger_team_goals,
                "goals_against_from_events": ledger_opponent_goals,
                "report_generated_after_full_time": True,
            },
        }

    factor = max(minutes / 90, 0.2)
    per90 = lambda value: round(float(value) / factor, 1)
    strengths: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []

    goal_sequences = [
        int(event["sequence"]) for event in events
        if event.get("kind") == "goal_for" and event.get("metadata", {}).get("contribution") == "goal"
    ]
    assist_sequences = [
        int(event["sequence"]) for event in events
        if event.get("kind") == "goal_for" and event.get("metadata", {}).get("contribution") == "assist"
    ]
    turnover_sequences = [int(event["sequence"]) for event in events if event.get("kind") == "player_turnover"]
    shot_sequences = [
        int(event["sequence"]) for event in events
        if event.get("kind") in {"goal_for", "player_shot_saved", "player_shot_off_target"}
        and event.get("metadata", {}).get("side") == "player"
    ]
    creative_sequences = [
        int(event["sequence"]) for event in events
        if event.get("kind") in {"player_key_pass", "goal_for"}
        and event.get("metadata", {}).get("contribution") == "assist"
        or event.get("kind") == "player_key_pass"
    ]

    if goals:
        strengths.append(_ranked_insight(
            92 + goals * 4,
            "Decisive finishing",
            f"Scored {goals} from {metrics['shots']} shots and {metrics['xg']:.2f} xG, directly changing the scoreline.",
            [_evidence("Goals", str(goals), goal_sequences), _evidence("Shots on target", str(metrics["shots_on_target"]), shot_sequences)],
        ))
    elif metrics["shots"] >= 3 and metrics["shots_on_target"] >= 2:
        strengths.append(_ranked_insight(
            64,
            "Shot generation",
            "Repeatedly reached shooting positions and forced saves, even though the chances were not converted.",
            [_evidence("Shots", str(metrics["shots"]), shot_sequences), _evidence("On target", str(metrics["shots_on_target"]), shot_sequences)],
        ))

    if assists:
        strengths.append(_ranked_insight(
            90 + assists * 3,
            "Direct chance creation",
            f"Registered {assists} assist{'s' if assists != 1 else ''} and supplied the decisive final pass.",
            [_evidence("Assists", str(assists), assist_sequences), _evidence("xA", f"{metrics['xa']:.2f}", creative_sequences)],
        ))
    elif metrics["key_passes"] >= 3:
        strengths.append(_ranked_insight(
            72,
            "Chance creation",
            f"Created {metrics['key_passes']} shooting opportunities and {metrics['big_chances_created']} big chances.",
            [_evidence("Key passes", str(metrics["key_passes"]), creative_sequences), _evidence("xA", f"{metrics['xa']:.2f}")],
        ))

    if metrics["pass_accuracy"] >= 86 and metrics["passes_attempted"] >= 20:
        strengths.append(_ranked_insight(
            68 + min(12, (metrics["pass_accuracy"] - 86) * 1.5),
            "Secure possession",
            "Kept the ball moving accurately while maintaining useful involvement.",
            [_evidence("Passing", f"{metrics['passes_completed']}/{metrics['passes_attempted']}"), _evidence("Accuracy", f"{metrics['pass_accuracy']:.0f}%")],
        ))

    if metrics["dribbles_completed"] >= 3 and metrics["dribble_success"] >= 55:
        strengths.append(_ranked_insight(
            66 + metrics["dribbles_completed"] * 2,
            "One-on-one progression",
            "Beat opponents often enough to carry the team through pressure and advance attacks.",
            [_evidence("Dribbles", f"{metrics['dribbles_completed']}/{metrics['dribbles_attempted']}")],
        ))

    if metrics["tackles_won"] >= 3 or (metrics["duels"] >= 5 and metrics["duel_win_rate"] >= 60):
        strengths.append(_ranked_insight(
            64 + metrics["tackles_won"] * 2,
            "Defensive competitiveness",
            "Won enough challenges to recover possession and disrupt opposition attacks.",
            [_evidence("Tackles won", str(metrics["tackles_won"])), _evidence("Duels", f"{metrics['duels_won']}/{metrics['duels']}")],
        ))

    if metrics["shots"] >= 3 and goals == 0:
        severity = 74 + min(20, metrics["xg"] * 10)
        gaps.append(_ranked_insight(
            severity,
            "Finishing efficiency",
            f"Failed to score from {metrics['shots']} shots and {metrics['xg']:.2f} xG; the quality of the final action did not match the positions reached.",
            [_evidence("Goals", "0", shot_sequences), _evidence("Shots on target", str(metrics["shots_on_target"]), shot_sequences)],
            "shooting",
        ))

    attacking_roles = {"CAM", "CM", "LW", "RW", "ST"}
    if position in attacking_roles and minutes >= 60 and assists == 0 and metrics["key_passes"] <= 1:
        gaps.append(_ranked_insight(
            72,
            "Limited creative influence",
            "Had enough minutes to affect the final third but produced too few passes that directly threatened goal.",
            [_evidence("Key passes", str(metrics["key_passes"]), creative_sequences), _evidence("xA", f"{metrics['xa']:.2f}")],
            "passing",
        ))

    if metrics["passes_attempted"] >= 15 and metrics["pass_accuracy"] < 72:
        gaps.append(_ranked_insight(
            70 + (72 - metrics["pass_accuracy"]),
            "Possession retention",
            "Passing accuracy was too low to sustain attacks and protect the team from transitions.",
            [_evidence("Passing", f"{metrics['passes_completed']}/{metrics['passes_attempted']}"), _evidence("Accuracy", f"{metrics['pass_accuracy']:.0f}%")],
            "passing",
        ))

    if metrics["turnovers"] >= 7:
        gaps.append(_ranked_insight(
            68 + metrics["turnovers"] * 2,
            "Turnover control",
            "Lost possession too frequently, including moments that exposed the team after the ball changed hands.",
            [_evidence("Turnovers", str(metrics["turnovers"]), turnover_sequences), _evidence("Turnovers per 90", str(per90(metrics["turnovers"])))],
            "dribbling",
        ))

    if metrics["duels"] >= 4 and metrics["duel_win_rate"] < 42:
        gaps.append(_ranked_insight(
            68 + (42 - metrics["duel_win_rate"]),
            "Duel resistance",
            "Lost too many physical contests, reducing impact on second balls and transitions.",
            [_evidence("Duels", f"{metrics['duels_won']}/{metrics['duels']}"), _evidence("Win rate", f"{metrics['duel_win_rate']:.0f}%")],
            "physical",
        ))

    if yellow_cards or red_cards or metrics["fouls_committed"] >= 3:
        gaps.append(_ranked_insight(
            78 + red_cards * 20 + yellow_cards * 5,
            "Discipline risk",
            "Fouls and cards created avoidable tactical and selection risk.",
            [_evidence("Fouls", str(metrics["fouls_committed"])), _evidence("Cards", f"{yellow_cards}Y / {red_cards}R")],
            "defending",
        ))

    if minutes >= 60 and metrics["touches"] < 28:
        gaps.append(_ranked_insight(
            62,
            "Low involvement",
            "Spent long periods outside the main flow of possession and did not receive the ball often enough.",
            [_evidence("Touches", str(metrics["touches"])), _evidence("Touches per 90", str(per90(metrics["touches"])))],
            "passing" if position in {"CM", "CAM", "CDM"} else "dribbling",
        ))

    strengths.sort(key=lambda item: item["score"], reverse=True)
    gaps.sort(key=lambda item: item["score"], reverse=True)

    if not strengths:
        strengths.append(_ranked_insight(
            50,
            "Reliable role execution",
            "Stayed connected to the match and completed the core responsibilities of the role, even without a decisive goal or assist.",
            [
                _evidence("Touches", str(metrics["touches"])),
                _evidence("Pass accuracy", f"{metrics['pass_accuracy']:.0f}%"),
                _evidence("Progressive actions", str(metrics["progressive_actions"])),
            ],
        ))
    if not gaps:
        gaps.append(_ranked_insight(
            40,
            "No major breakdown",
            "No single weakness materially damaged the performance. The next step is balanced role refinement rather than correcting a specific failure.",
            [
                _evidence("Rating", f"{rating:.1f}"),
                _evidence("Minutes", str(minutes)),
                _evidence("Progressive actions", str(metrics["progressive_actions"])),
            ],
            "balanced",
        ))

    action_map = {
        "shooting": ("Finishing under pressure", "Rehearse shot selection, body shape and composure from the exact zones reached in this match."),
        "passing": ("Decision and release speed", "Train scanning before reception and the weight of passes under pressure."),
        "dribbling": ("Ball security", "Reduce unnecessary carries and improve the decision to release or protect possession."),
        "physical": ("Contact and balance", "Improve strength, balance and repeat-effort capacity in contested actions."),
        "defending": ("Defensive timing", "Improve body position and challenge timing to reduce recovery fouls and lost duels."),
        "balanced": ("Role refinement", "Continue developing the core demands of the current role."),
    }
    actions = []
    seen_focus = set()
    for gap in gaps:
        focus = gap.get("focus", "balanced")
        if focus in seen_focus:
            continue
        seen_focus.add(focus)
        title, detail = action_map[focus]
        actions.append({
            "focus": focus,
            "title": title,
            "detail": detail,
            "evidence": gap.get("evidence", []),
        })
        if len(actions) == 3:
            break

    if motm:
        headline = f"Player of the Match in a {scoreline} {result_word}"
    elif goals + assists >= 2:
        headline = f"Decisive contribution in a {scoreline} {result_word}"
    elif goals:
        headline = f"A goal shapes the {scoreline} {result_word}"
    elif assists:
        headline = f"A decisive pass in the {scoreline} {result_word}"
    elif rating >= 7.4:
        headline = f"Strong influence across {minutes} minutes"
    else:
        headline = f"{minutes} minutes assessed in a {scoreline} {result_word}"

    if rating >= 8.5:
        grade = "decisive, high-impact"
    elif rating >= 7.4:
        grade = "strong and clearly positive"
    elif rating >= 6.5:
        grade = "solid with useful contributions"
    elif rating >= 5.8:
        grade = "mixed with limited decisive influence"
    else:
        grade = "difficult with costly weaknesses"

    turning_candidates = [
        event for event in events
        if event.get("kind") in {
            "goal_for", "goal_against", "red_card", "injury",
            "player_key_pass", "player_turnover", "player_shot_saved",
        }
    ]
    turning_points = [
        {"minute": event["minute"], "text": event["text"], "event_sequence": event["sequence"]}
        for event in turning_candidates[:6]
    ]

    return {
        "schema_version": 2,
        "source": "sealed_event_ledger",
        "headline": headline,
        "verdict": f"{player_name} produced a {grade} performance, rated {rating:.1f} over {minutes} minutes.",
        "result_context": _describe_score_flow(goal_events, team_goals, opponent_goals, result_word, scoreline),
        "turning_points": turning_points,
        "strengths": strengths[:3],
        "gaps": gaps[:3],
        "coaching_actions": actions[:3],
        "metrics": metrics,
        "trace": {
            "event_count": len(events),
            "source_event_sequences": [int(event["sequence"]) for event in player_events],
            "goals_from_events": ledger_team_goals,
            "goals_against_from_events": ledger_opponent_goals,
            "report_generated_after_full_time": True,
        },
    }


def _describe_score_flow(goal_events, team_goals, opponent_goals, result_word, scoreline):
    if not goal_events:
        return f"The match finished {scoreline}; neither side created a scoring event in the sealed ledger."
    first = goal_events[0]
    last = goal_events[-1]
    first_side = "your team" if first["kind"] == "goal_for" else "the opposition"
    last_side = "your team" if last["kind"] == "goal_for" else "the opposition"
    if first["kind"] == "goal_against" and team_goals >= opponent_goals:
        return f"The opposition scored first at {first['minute']}', but your team recovered to finish with a {scoreline} {result_word}. The final scoring event belonged to {last_side} at {last['minute']}'."
    if first["kind"] == "goal_for" and team_goals <= opponent_goals:
        return f"Your team opened the scoring at {first['minute']}' but could not protect the advantage, ending in a {scoreline} {result_word}. The final scoring event belonged to {last_side} at {last['minute']}'."
    return f"{first_side.capitalize()} opened the scoring at {first['minute']}'. The match ended in a {scoreline} {result_word}, with the last goal scored by {last_side} at {last['minute']}'."


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
    involvement = max(0.03, min(0.78, (0.15 + attacking_weight * 0.25 + (overall - 50) / 180) * minutes_factor))

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

    metrics = _simulate_player_metrics(
        position=position,
        overall=overall,
        fitness=fitness,
        minutes=minutes,
        goals=goals,
        assists=assists,
        physical=physical,
        defending=defending,
        rng=rng,
    )
    rating = _rating_from_metrics(
        metrics=metrics,
        goals=goals,
        assists=assists,
        yellow_cards=yellow_cards,
        red_cards=red_cards,
        injured=injured,
        fitness=fitness,
        morale=morale,
        team_goals=team_goals,
        opponent_goals=opponent_goals,
        selection_status=selection_status,
        rng=rng,
    )
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
        metrics=metrics,
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
        "metrics": metrics,
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
