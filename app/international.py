from __future__ import annotations

import json
import random
from typing import Any

from .calendar_engine import nations_league_active, tournament_for_season
from .world import nationality_country_code


NATIONAL_TEAM_RATINGS = {
    "ENG": 88,
    "ESP": 89,
    "ITA": 86,
    "GER": 87,
    "FRA": 90,
    "POR": 86,
    "NED": 86,
    "SCO": 76,
    "IRL": 71,
    "USA": 79,
    "BRA": 91,
    "ARG": 91,
    "KSA": 72,
    "JPN": 80,
    "AUS": 77,
    "IND": 52,
}

POSITION_ATTACK = {
    "ST": 1.00,
    "LW": 0.82,
    "RW": 0.82,
    "CAM": 0.68,
    "CM": 0.36,
    "CDM": 0.14,
    "LB": 0.12,
    "RB": 0.12,
    "CB": 0.06,
    "GK": 0.00,
}

POSITION_CREATION = {
    "ST": 0.28,
    "LW": 0.62,
    "RW": 0.62,
    "CAM": 0.90,
    "CM": 0.78,
    "CDM": 0.38,
    "LB": 0.42,
    "RB": 0.42,
    "CB": 0.10,
    "GK": 0.03,
}


def seed_national_teams(db) -> None:
    countries = db.execute("SELECT id, code, name, confederation FROM countries WHERE code <> 'LGC'").fetchall()
    for country in countries:
        rating = NATIONAL_TEAM_RATINGS.get(country["code"], 68)
        db.execute(
            """
            INSERT INTO national_teams(country_id, name, short_name, confederation, rating, reputation)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(country_id) DO UPDATE SET
                name=excluded.name, short_name=excluded.short_name,
                confederation=excluded.confederation, rating=excluded.rating,
                reputation=excluded.reputation
            """,
            (country["id"], country["name"], country["code"], country["confederation"], rating, rating),
        )


def _national_team_for_career(db, career):
    code = nationality_country_code(career["nationality"])
    if not code:
        return None
    return db.execute(
        """
        SELECT nt.*, co.name AS country_name, co.code AS country_code
        FROM national_teams nt JOIN countries co ON co.id=nt.country_id
        WHERE co.code=?
        """,
        (code,),
    ).fetchone()


def _season_form(db, career_id: int, season_number: int) -> dict[str, float]:
    row = db.execute(
        """
        SELECT appearances, goals, assists, motm,
               CASE WHEN appearances=0 THEN 0 ELSE rating_total/appearances END AS average_rating
        FROM season_player_stats WHERE career_id=? AND season_number=?
        """,
        (career_id, season_number),
    ).fetchone()
    return dict(row) if row else {"appearances": 0, "goals": 0, "assists": 0, "motm": 0, "average_rating": 0.0}


def _competition_for_window(career, team, calendar_week: int) -> str:
    tournament = tournament_for_season(career["season_label"], team["confederation"])
    if tournament and calendar_week >= 49:
        return tournament
    if nations_league_active(career["season_label"], team["confederation"]) and calendar_week in {14, 15, 21, 36}:
        return "UEFA Nations League"
    if calendar_week in {14, 15, 21, 36, 48}:
        if tournament:
            return f"{tournament} preparation / qualification"
        return "International qualifiers and friendlies"
    return "International programme"


def _qualified_for_tournament(db, career, team, tournament: str, rng: random.Random) -> bool:
    existing = db.execute(
        """
        SELECT qualified FROM national_team_campaigns
        WHERE career_id=? AND season_number=? AND national_team_id=? AND competition_name=?
        """,
        (career["id"], career["season_number"], team["id"], tournament),
    ).fetchone()
    if existing is not None:
        return bool(existing["qualified"])
    base = 0.12 + max(0, team["rating"] - 55) / 45
    if tournament == "FIFA World Cup":
        base -= 0.08
    qualified = rng.random() < max(0.08, min(0.98, base))
    db.execute(
        """
        INSERT INTO national_team_campaigns(
            career_id, season_number, national_team_id, competition_name,
            qualified, stage, points, metadata_json
        ) VALUES (?, ?, ?, ?, ?, 'qualification', 0, ?)
        """,
        (
            career["id"], career["season_number"], team["id"], tournament,
            int(qualified), json.dumps({"team_rating": team["rating"]}, sort_keys=True),
        ),
    )
    return qualified


def _callup_probability(career, team, form: dict[str, float]) -> tuple[float, float]:
    player_score = (
        career["overall"] * 0.72
        + career["reputation"] * 0.11
        + career["national_team_reputation"] * 0.07
        + form["average_rating"] * 1.35
        + min(6.0, (form["goals"] + form["assists"]) * 0.18)
    )
    threshold = team["rating"] - 7.5
    probability = 0.08 + (player_score - threshold) / 24
    if form["appearances"] < 3:
        probability -= 0.12
    return max(0.02, min(0.96, probability)), player_score


def _simulate_player_window(career, team, competition: str, match_count: int, rng: random.Random) -> dict[str, Any]:
    position = career["position"]
    attack = POSITION_ATTACK.get(position, 0.35)
    creation = POSITION_CREATION.get(position, 0.35)
    starts = 0
    appearances = 0
    minutes = 0
    goals = 0
    assists = 0
    ratings: list[float] = []
    team_results: list[str] = []

    for _ in range(match_count):
        start_probability = max(0.18, min(0.90, 0.42 + (career["overall"] - team["rating"] + 8) / 32))
        started = rng.random() < start_probability
        appeared = started or rng.random() < 0.72
        if not appeared:
            team_results.append(rng.choice(["W", "D", "L"]))
            continue
        appearances += 1
        starts += int(started)
        match_minutes = rng.randint(68, 95) if started else rng.randint(12, 36)
        minutes += match_minutes
        factor = match_minutes / 90
        goal_probability = max(0.01, (0.05 + attack * 0.30 + (career["overall"] - 55) * 0.004) * factor)
        assist_probability = max(0.01, (0.04 + creation * 0.23 + (career["passing"] - 50) * 0.003) * factor)
        match_goals = int(rng.random() < min(0.72, goal_probability))
        if match_goals and rng.random() < 0.08:
            match_goals += 1
        match_assists = int(rng.random() < min(0.64, assist_probability))
        goals += match_goals
        assists += match_assists
        rating = 6.15 + match_goals * 1.05 + match_assists * 0.72 + rng.uniform(-0.55, 0.70)
        ratings.append(round(max(4.5, min(9.8, rating)), 1))
        result_roll = rng.random() + (team["rating"] - 70) / 100
        team_results.append("W" if result_roll > 0.72 else "D" if result_roll > 0.42 else "L")

    return {
        "competition": competition,
        "matches": match_count,
        "appearances": appearances,
        "starts": starts,
        "minutes": minutes,
        "goals": goals,
        "assists": assists,
        "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0.0,
        "team_results": team_results,
    }


def process_international_week(db, career, calendar_week: int, rng: random.Random) -> dict[str, Any] | None:
    team = _national_team_for_career(db, career)
    if team is None:
        return None
    if calendar_week not in {14, 15, 21, 36, 48, 49, 50, 51, 52}:
        return None
    if db.execute(
        """
        SELECT 1 FROM national_team_callups
        WHERE career_id=? AND season_number=? AND calendar_week=?
        """,
        (career["id"], career["season_number"], calendar_week),
    ).fetchone():
        return {"status": "already_processed"}

    competition = _competition_for_window(career, team, calendar_week)
    tournament = tournament_for_season(career["season_label"], team["confederation"])
    if calendar_week >= 49:
        if not tournament:
            return None
        if not _qualified_for_tournament(db, career, team, tournament, rng):
            db.execute(
                """
                INSERT INTO national_team_callups(
                    career_id, season_number, calendar_week, national_team_id,
                    competition_name, selected, reason, status
                ) VALUES (?, ?, ?, ?, ?, 0, ?, 'not_qualified')
                """,
                (career["id"], career["season_number"], calendar_week, team["id"], tournament, f"{team['country_name']} did not qualify"),
            )
            db.execute("UPDATE careers SET fitness=MIN(100, fitness+8), morale=MIN(100, morale+2) WHERE id=?", (career["id"],))
            return {"status": "not_qualified", "competition": tournament, "team": team["country_name"]}

    form = _season_form(db, career["id"], career["season_number"])
    probability, score = _callup_probability(career, team, form)
    if calendar_week >= 49:
        probability += 0.08
    selected = rng.random() < min(0.98, probability)
    if not selected:
        reason = f"Selection score {score:.1f}; squad threshold around {team['rating'] - 7.5:.1f}"
        db.execute(
            """
            INSERT INTO national_team_callups(
                career_id, season_number, calendar_week, national_team_id,
                competition_name, selected, selection_score, reason, status
            ) VALUES (?, ?, ?, ?, ?, 0, ?, ?, 'not_selected')
            """,
            (career["id"], career["season_number"], calendar_week, team["id"], competition, score, reason),
        )
        db.execute(
            "UPDATE careers SET fitness=MIN(100, fitness+10), morale=MIN(100, morale+1), national_team_status='not_selected' WHERE id=?",
            (career["id"],),
        )
        return {"status": "not_selected", "competition": competition, "team": team["country_name"], "reason": reason}

    match_count = 1 if calendar_week in {49, 50, 51, 52} else 2
    performance = _simulate_player_window(career, team, competition, match_count, rng)
    callup = db.execute(
        """
        INSERT INTO national_team_callups(
            career_id, season_number, calendar_week, national_team_id,
            competition_name, selected, selection_score, reason, status,
            appearances, starts, minutes, goals, assists, average_rating, results_json
        ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, 'selected', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            career["id"], career["season_number"], calendar_week, team["id"], competition,
            score, "Selected on ability, reputation and current-season form",
            performance["appearances"], performance["starts"], performance["minutes"],
            performance["goals"], performance["assists"], performance["average_rating"],
            json.dumps(performance["team_results"]),
        ),
    )
    db.execute(
        """
        INSERT INTO international_player_stats(
            career_id, appearances, starts, minutes, goals, assists, rating_total
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(career_id) DO UPDATE SET
            appearances=appearances+excluded.appearances,
            starts=starts+excluded.starts,
            minutes=minutes+excluded.minutes,
            goals=goals+excluded.goals,
            assists=assists+excluded.assists,
            rating_total=rating_total+(excluded.rating_total)
        """,
        (
            career["id"], performance["appearances"], performance["starts"], performance["minutes"],
            performance["goals"], performance["assists"], performance["average_rating"] * performance["appearances"],
        ),
    )
    reputation_gain = min(6, performance["appearances"] + performance["goals"] * 2 + performance["assists"])
    fatigue = min(18, round(performance["minutes"] / 18))
    appearance_fee = performance["appearances"] * max(250, team["rating"] * 15)
    db.execute(
        """
        UPDATE careers SET
            national_team_status='selected',
            national_team_reputation=MIN(100, national_team_reputation+?),
            reputation=MIN(100, reputation+?),
            fitness=MAX(35, fitness-?),
            morale=MIN(100, morale+?),
            money=money+?
        WHERE id=?
        """,
        (
            reputation_gain, max(1, reputation_gain // 2), fatigue,
            4 if performance["appearances"] else 1, appearance_fee, career["id"],
        ),
    )
    if appearance_fee:
        db.execute(
            """
            INSERT INTO finance_transactions(
                career_id, season_number, week, calendar_week, category, amount, description
            ) VALUES (?, ?, ?, ?, 'International duty', ?, ?)
            """,
            (
                career["id"], career["season_number"], career["current_week"], calendar_week,
                appearance_fee, f"{team['country_name']} appearance fees — {competition}",
            ),
        )
    return {
        "status": "selected",
        "competition": competition,
        "team": team["country_name"],
        "callup_id": callup.lastrowid,
        **performance,
    }


def get_international_summary(db, career_id: int) -> dict[str, Any]:
    career = db.execute("SELECT * FROM careers WHERE id=?", (career_id,)).fetchone()
    if career is None:
        return {"team": None, "stats": None, "recent": []}
    team = _national_team_for_career(db, career)
    stats = db.execute(
        """
        SELECT *, CASE WHEN appearances=0 THEN 0 ELSE ROUND(rating_total/appearances, 2) END AS average_rating
        FROM international_player_stats WHERE career_id=?
        """,
        (career_id,),
    ).fetchone()
    recent = db.execute(
        """
        SELECT c.*, nt.name AS national_team_name
        FROM national_team_callups c JOIN national_teams nt ON nt.id=c.national_team_id
        WHERE c.career_id=? ORDER BY c.season_number DESC, c.calendar_week DESC LIMIT 8
        """,
        (career_id,),
    ).fetchall()
    return {"team": team, "stats": stats, "recent": recent}
