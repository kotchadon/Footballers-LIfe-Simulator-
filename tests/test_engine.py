import random

from app.engine import player_selection_probability, simulate_player_performance, simulate_score


def test_match_score_is_non_negative():
    result = simulate_score(70, 65, random.Random(1))
    assert result.home_goals >= 0
    assert result.away_goals >= 0


def test_selection_probability_is_bounded():
    assert 0.0 <= player_selection_probability(10, 99, 20, 20) <= 1.0
    assert 0.0 <= player_selection_probability(99, 10, 100, 100) <= 1.0


def test_player_performance_has_valid_rating():
    performance = simulate_player_performance(
        player_name="Test Player",
        position="ST",
        overall=70,
        fitness=90,
        morale=80,
        team_goals=3,
        opponent_goals=1,
        rng=random.Random(5),
    )
    assert 3.5 <= performance["rating"] <= 10.0
    assert performance["goals"] >= 0
    assert performance["assists"] >= 0
