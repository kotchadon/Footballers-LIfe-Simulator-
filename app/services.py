from __future__ import annotations

import random
from collections import defaultdict

from .db import get_db
from .engine import player_selection_probability, simulate_player_performance, simulate_score

CLUBS = [
    ("North London Red", "NLR", 70, 78),
    ("Manchester Sky", "MCS", 74, 84),
    ("Merseyside Red", "MER", 72, 82),
    ("West London Blue", "WLB", 69, 77),
    ("Birmingham Lions", "BIR", 64, 66),
    ("Newcastle Black", "NEW", 67, 72),
    ("Brighton Coast", "BRI", 63, 61),
    ("Nottingham Forest Green", "NFG", 61, 59),
]


def seed_clubs():
    db = get_db()
    db.executemany(
        "INSERT OR IGNORE INTO clubs(name, short_name, strength, reputation) VALUES (?, ?, ?, ?)",
        CLUBS,
    )
    db.commit()


def round_robin(team_ids):
    teams = list(team_ids)
    if len(teams) % 2:
        teams.append(None)
    rounds = []
    for round_index in range(len(teams) - 1):
        fixtures = []
        for i in range(len(teams) // 2):
            a, b = teams[i], teams[-1 - i]
            if a is not None and b is not None:
                if round_index % 2 == 0:
                    fixtures.append((a, b))
                else:
                    fixtures.append((b, a))
        rounds.append(fixtures)
        teams = [teams[0], teams[-1], *teams[1:-1]]
    second_half = [[(away, home) for home, away in fixtures] for fixtures in rounds]
    return rounds + second_half


def create_career(player_name, nationality, position):
    seed_clubs()
    db = get_db()
    starting_club = db.execute("SELECT * FROM clubs ORDER BY strength ASC LIMIT 1").fetchone()
    cursor = db.execute(
        """
        INSERT INTO careers(player_name, nationality, position, club_id)
        VALUES (?, ?, ?, ?)
        """,
        (player_name.strip(), nationality.strip(), position, starting_club["id"]),
    )
    career_id = cursor.lastrowid
    db.execute("INSERT INTO player_stats(career_id) VALUES (?)", (career_id,))

    clubs = db.execute("SELECT id FROM clubs ORDER BY id").fetchall()
    club_ids = [row["id"] for row in clubs]
    for club_id in club_ids:
        db.execute("INSERT INTO standings(career_id, club_id) VALUES (?, ?)", (career_id, club_id))

    for week, fixtures in enumerate(round_robin(club_ids), start=1):
        for home_id, away_id in fixtures:
            db.execute(
                "INSERT INTO fixtures(career_id, week, home_club_id, away_club_id) VALUES (?, ?, ?, ?)",
                (career_id, week, home_id, away_id),
            )
    db.commit()
    return career_id


def get_active_career():
    return get_db().execute(
        """
        SELECT careers.*, clubs.name AS club_name, clubs.short_name, clubs.strength AS club_strength
        FROM careers JOIN clubs ON clubs.id = careers.club_id
        ORDER BY careers.id DESC LIMIT 1
        """
    ).fetchone()


def get_standings(career_id):
    return get_db().execute(
        """
        SELECT clubs.name, clubs.short_name, standings.*,
               (standings.goals_for - standings.goals_against) AS goal_difference
        FROM standings JOIN clubs ON clubs.id = standings.club_id
        WHERE standings.career_id = ?
        ORDER BY standings.points DESC, goal_difference DESC, standings.goals_for DESC, clubs.name
        """,
        (career_id,),
    ).fetchall()


def get_next_player_fixture(career):
    return get_db().execute(
        """
        SELECT fixtures.*, home.name AS home_name, away.name AS away_name
        FROM fixtures
        JOIN clubs home ON home.id = fixtures.home_club_id
        JOIN clubs away ON away.id = fixtures.away_club_id
        WHERE fixtures.career_id = ? AND fixtures.week = ?
          AND (fixtures.home_club_id = ? OR fixtures.away_club_id = ?)
        LIMIT 1
        """,
        (career["id"], career["current_week"], career["club_id"], career["club_id"]),
    ).fetchone()


def update_standing(career_id, club_id, goals_for, goals_against):
    won = int(goals_for > goals_against)
    drawn = int(goals_for == goals_against)
    lost = int(goals_for < goals_against)
    points = won * 3 + drawn
    get_db().execute(
        """
        UPDATE standings
        SET played = played + 1,
            won = won + ?, drawn = drawn + ?, lost = lost + ?,
            goals_for = goals_for + ?, goals_against = goals_against + ?,
            points = points + ?
        WHERE career_id = ? AND club_id = ?
        """,
        (won, drawn, lost, goals_for, goals_against, points, career_id, club_id),
    )


def play_next_week(career_id, seed=None):
    rng = random.Random(seed)
    db = get_db()
    career = db.execute(
        """
        SELECT careers.*, clubs.strength AS club_strength
        FROM careers JOIN clubs ON clubs.id = careers.club_id
        WHERE careers.id = ?
        """,
        (career_id,),
    ).fetchone()
    if career is None:
        raise ValueError("Career not found")

    week = career["current_week"]
    fixtures = db.execute(
        """
        SELECT f.*, h.strength AS home_strength, a.strength AS away_strength,
               h.name AS home_name, a.name AS away_name
        FROM fixtures f
        JOIN clubs h ON h.id = f.home_club_id
        JOIN clubs a ON a.id = f.away_club_id
        WHERE f.career_id = ? AND f.week = ? AND f.played = 0
        """,
        (career_id, week),
    ).fetchall()
    if not fixtures:
        return None

    player_report = None
    for fixture in fixtures:
        result = simulate_score(fixture["home_strength"], fixture["away_strength"], rng)
        db.execute(
            "UPDATE fixtures SET played = 1, home_goals = ?, away_goals = ? WHERE id = ?",
            (result.home_goals, result.away_goals, fixture["id"]),
        )
        update_standing(career_id, fixture["home_club_id"], result.home_goals, result.away_goals)
        update_standing(career_id, fixture["away_club_id"], result.away_goals, result.home_goals)

        is_player_fixture = career["club_id"] in (fixture["home_club_id"], fixture["away_club_id"])
        if not is_player_fixture:
            continue

        probability = player_selection_probability(
            career["overall"], career["club_strength"], career["fitness"], career["morale"]
        )
        started = rng.random() < probability
        player_team_is_home = career["club_id"] == fixture["home_club_id"]
        team_goals = result.home_goals if player_team_is_home else result.away_goals
        opponent_goals = result.away_goals if player_team_is_home else result.home_goals

        if started:
            performance = simulate_player_performance(
                player_name=career["player_name"],
                position=career["position"],
                overall=career["overall"],
                fitness=career["fitness"],
                morale=career["morale"],
                team_goals=team_goals,
                opponent_goals=opponent_goals,
                rng=rng,
            )
        else:
            performance = {
                "goals": 0,
                "assists": 0,
                "rating": 0.0,
                "motm": False,
                "commentary": "The manager leaves you out of the starting XI this week.",
            }

        win = int(team_goals > opponent_goals)
        draw = int(team_goals == opponent_goals)
        loss = int(team_goals < opponent_goals)
        if started:
            db.execute(
                """
                UPDATE player_stats
                SET appearances = appearances + 1,
                    starts = starts + 1,
                    goals = goals + ?, assists = assists + ?,
                    motm = motm + ?, rating_total = rating_total + ?,
                    wins = wins + ?, draws = draws + ?, losses = losses + ?
                WHERE career_id = ?
                """,
                (
                    performance["goals"], performance["assists"], int(performance["motm"]),
                    performance["rating"], win, draw, loss, career_id,
                ),
            )

        db.execute(
            """
            INSERT INTO match_reports(
                career_id, week, fixture_id, player_started, player_goals,
                player_assists, player_rating, player_motm, commentary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                career_id, week, fixture["id"], int(started), performance["goals"],
                performance["assists"], performance["rating"], int(performance["motm"]),
                performance["commentary"],
            ),
        )

        fitness_change = rng.randint(-10, -5) if started else rng.randint(2, 5)
        morale_change = rng.randint(-2, 4) + (2 if win else -2 if loss else 0)
        development_roll = 1 if started and performance["rating"] >= 7.5 and rng.random() < 0.3 else 0
        db.execute(
            """
            UPDATE careers
            SET fitness = MIN(100, MAX(35, fitness + ?)),
                morale = MIN(100, MAX(20, morale + ?)),
                overall = MIN(potential, overall + ?),
                reputation = MIN(100, reputation + ?)
            WHERE id = ?
            """,
            (
                fitness_change,
                morale_change,
                development_roll,
                performance["goals"] * 2 + performance["assists"] + int(performance["motm"]),
                career_id,
            ),
        )
        player_report = {
            "fixture_id": fixture["id"],
            "home_name": fixture["home_name"],
            "away_name": fixture["away_name"],
            "home_goals": result.home_goals,
            "away_goals": result.away_goals,
            "started": started,
            **performance,
        }

    max_week = db.execute("SELECT MAX(week) AS max_week FROM fixtures WHERE career_id = ?", (career_id,)).fetchone()["max_week"]
    next_week = week + 1
    if next_week > max_week:
        next_week = max_week + 1
    db.execute("UPDATE careers SET current_week = ? WHERE id = ?", (next_week, career_id))
    db.commit()
    return player_report


def recover_player(career_id):
    db = get_db()
    db.execute(
        "UPDATE careers SET fitness = MIN(100, fitness + 12), morale = MIN(100, morale + 2) WHERE id = ?",
        (career_id,),
    )
    db.commit()


def get_stats(career_id):
    return get_db().execute(
        """
        SELECT *, CASE WHEN appearances = 0 THEN 0 ELSE ROUND(rating_total / appearances, 2) END AS average_rating
        FROM player_stats WHERE career_id = ?
        """,
        (career_id,),
    ).fetchone()


def get_recent_reports(career_id, limit=5):
    return get_db().execute(
        """
        SELECT mr.*, f.home_goals, f.away_goals, h.name AS home_name, a.name AS away_name
        FROM match_reports mr
        JOIN fixtures f ON f.id = mr.fixture_id
        JOIN clubs h ON h.id = f.home_club_id
        JOIN clubs a ON a.id = f.away_club_id
        WHERE mr.career_id = ? ORDER BY mr.id DESC LIMIT ?
        """,
        (career_id, limit),
    ).fetchall()


def get_week_results(career_id, week):
    return get_db().execute(
        """
        SELECT f.*, h.name AS home_name, a.name AS away_name
        FROM fixtures f
        JOIN clubs h ON h.id = f.home_club_id
        JOIN clubs a ON a.id = f.away_club_id
        WHERE f.career_id = ? AND f.week = ? AND f.played = 1
        ORDER BY f.id
        """,
        (career_id, week),
    ).fetchall()
