import random

from app.engine import (
    calculate_overall,
    create_starting_attributes,
    player_selection_probability,
    simulate_player_performance,
    simulate_score,
)


def test_match_score_is_non_negative():
    result = simulate_score(70, 65, random.Random(1))
    assert result.home_goals >= 0
    assert result.away_goals >= 0


def test_selection_probability_is_bounded():
    assert 0.0 <= player_selection_probability(10, 99, 20, 20) <= 1.0
    assert 0.0 <= player_selection_probability(99, 10, 100, 100) <= 1.0


def test_starting_attributes_and_overall_are_valid():
    attributes = create_starting_attributes("ST", random.Random(2))
    assert set(attributes) == {"pace", "shooting", "passing", "dribbling", "defending", "physical"}
    overall = calculate_overall(attributes, "ST", potential=88)
    assert 35 <= overall <= 88


def test_player_performance_has_score_consistent_replay_events():
    performance = simulate_player_performance(
        player_name="Test Player",
        position="ST",
        overall=70,
        fitness=90,
        morale=80,
        team_goals=3,
        opponent_goals=1,
        minutes=90,
        selection_status="starter",
        physical=65,
        defending=30,
        rng=random.Random(5),
    )
    assert 3.5 <= performance["rating"] <= 10.0
    assert performance["goals"] >= 0
    assert performance["assists"] >= 0
    assert performance["injury_weeks"] >= 0
    assert sum(event["kind"] == "goal_for" for event in performance["events"]) == 3
    assert sum(event["kind"] == "goal_against" for event in performance["events"]) == 1


def test_substitute_gets_reduced_minutes_and_entrance_event():
    performance = simulate_player_performance(
        player_name="Impact Sub",
        position="CAM",
        overall=62,
        fitness=82,
        morale=70,
        team_goals=2,
        opponent_goals=2,
        minutes=22,
        selection_status="substitute",
        rng=random.Random(9),
    )
    assert 3.5 <= performance["rating"] <= 10.0
    assert "comes off the bench" in performance["commentary"]
