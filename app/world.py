from __future__ import annotations

import json
import random
from collections import defaultdict
from typing import Any

from .world_data import (
    ALL_LEAGUES,
    COMPETITIONS,
    NATIONALITY_TO_COUNTRY_CODE,
    iter_club_rows,
)


def _round_robin(team_ids: list[int]) -> list[list[tuple[int, int]]]:
    teams = list(team_ids)
    if len(teams) % 2:
        teams.append(None)
    rounds: list[list[tuple[int, int]]] = []
    for round_index in range(len(teams) - 1):
        pairs: list[tuple[int, int]] = []
        for index in range(len(teams) // 2):
            a = teams[index]
            b = teams[-(index + 1)]
            if a is None or b is None:
                continue
            pairs.append((a, b) if (round_index + index) % 2 == 0 else (b, a))
        rounds.append(pairs)
        teams = [teams[0], teams[-1], *teams[1:-1]]
    return rounds + [[(away, home) for home, away in round_pairs] for round_pairs in rounds]


def seed_world_database(db) -> None:
    """Idempotently seed countries, leagues, clubs, units and competition catalogue."""
    countries: dict[str, tuple[str, str]] = {}
    for league in ALL_LEAGUES:
        countries[league.country_code] = (league.country, league.confederation)
    for code, (name, confederation) in countries.items():
        db.execute(
            "INSERT INTO countries(code, name, confederation) VALUES (?, ?, ?) "
            "ON CONFLICT(code) DO UPDATE SET name=excluded.name, confederation=excluded.confederation",
            (code, name, confederation),
        )

    country_ids = {row["code"]: row["id"] for row in db.execute("SELECT id, code FROM countries")}
    for league in ALL_LEAGUES:
        rules = {
            "points_win": 3,
            "points_draw": 1,
            "schedule": "double_round_robin",
            "promotion_slots": league.promotion_slots,
            "relegation_slots": league.relegation_slots,
            "playoff_slots": league.playoff_slots,
        }
        db.execute(
            """
            INSERT INTO leagues(
                code, country_id, name, tier, reputation, team_count,
                promotion_slots, relegation_slots, playoff_slots, fully_playable, rules_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name=excluded.name, reputation=excluded.reputation, team_count=excluded.team_count,
                promotion_slots=excluded.promotion_slots, relegation_slots=excluded.relegation_slots,
                playoff_slots=excluded.playoff_slots, fully_playable=excluded.fully_playable,
                rules_json=excluded.rules_json
            """,
            (
                league.code, country_ids[league.country_code], league.name, league.tier,
                league.reputation, len(league.clubs), league.promotion_slots,
                league.relegation_slots, league.playoff_slots, int(league.fully_playable),
                json.dumps(rules, sort_keys=True),
            ),
        )

    league_ids = {row["code"]: row["id"] for row in db.execute("SELECT id, code FROM leagues")}
    for club in iter_club_rows():
        db.execute(
            """
            INSERT INTO clubs(
                name, short_name, strength, reputation, country_id, league_id,
                youth_rating, reserve_rating, is_real
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(name) DO UPDATE SET
                strength=excluded.strength, reputation=excluded.reputation,
                country_id=excluded.country_id, league_id=excluded.league_id,
                youth_rating=excluded.youth_rating, reserve_rating=excluded.reserve_rating,
                is_real=1
            """,
            (
                club["name"], club["short_name"], club["strength"], club["reputation"],
                country_ids[club["country_code"]], league_ids[club["league_code"]],
                club["youth_rating"], club["reserve_rating"],
            ),
        )

    for row in db.execute("SELECT id, strength, youth_rating, reserve_rating FROM clubs WHERE is_real = 1"):
        units = (
            ("first_team", row["strength"], max(45, row["youth_rating"] - 4)),
            ("reserve", row["reserve_rating"], row["youth_rating"]),
            ("u18", max(38, row["reserve_rating"] - 8), min(99, row["youth_rating"] + 4)),
        )
        for unit_type, strength, development in units:
            db.execute(
                """
                INSERT INTO club_units(club_id, unit_type, strength, development_rating)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(club_id, unit_type) DO UPDATE SET
                    strength=excluded.strength, development_rating=excluded.development_rating
                """,
                (row["id"], unit_type, strength, development),
            )

    for code, name, country_name, competition_type, confederation, reputation in COMPETITIONS:
        country_id = None
        if country_name:
            country_row = db.execute("SELECT id FROM countries WHERE name = ?", (country_name,)).fetchone()
            country_id = country_row["id"] if country_row else None
        format_payload = _competition_format(code, competition_type)
        status = "active_foundation" if competition_type in {"domestic_cup", "continental_club"} else "catalogued"
        db.execute(
            """
            INSERT INTO competitions(
                code, name, country_id, competition_type, confederation,
                reputation, simulation_status, format_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name=excluded.name, country_id=excluded.country_id,
                competition_type=excluded.competition_type, confederation=excluded.confederation,
                reputation=excluded.reputation, simulation_status=excluded.simulation_status,
                format_json=excluded.format_json
            """,
            (code, name, country_id, competition_type, confederation, reputation, status, json.dumps(format_payload, sort_keys=True)),
        )


def _competition_format(code: str, competition_type: str) -> dict[str, Any]:
    if code in {"UCL", "UEL"}:
        return {"teams": 36, "phase": "league", "league_matches": 8, "top_8": "round_of_16", "places_9_24": "playoff"}
    if code == "WC":
        return {"teams": 48, "groups": 12, "group_size": 4, "knockout_from": 32}
    if competition_type == "domestic_cup":
        return {"phase": "knockout", "legs": 1, "extra_time": True, "penalties": True}
    if competition_type == "continental_club":
        return {"phase": "configured_by_confederation"}
    return {"phase": "catalogue"}


def migrate_legacy_world(db) -> None:
    """Attach older fictional saves to an isolated legacy league without data loss."""
    legacy_clubs = db.execute("SELECT id FROM clubs WHERE league_id IS NULL").fetchall()
    if legacy_clubs:
        db.execute(
            "INSERT INTO countries(code, name, confederation) VALUES ('LGC', 'Legacy Sandbox', 'SANDBOX') "
            "ON CONFLICT(code) DO NOTHING"
        )
        country_id = db.execute("SELECT id FROM countries WHERE code='LGC'").fetchone()["id"]
        db.execute(
            """
            INSERT INTO leagues(code, country_id, name, tier, reputation, team_count, fully_playable, rules_json)
            VALUES ('LGC1', ?, 'Legacy Premier Division', 1, 50, ?, 1, '{}')
            ON CONFLICT(code) DO UPDATE SET team_count=excluded.team_count
            """,
            (country_id, len(legacy_clubs)),
        )
        league_id = db.execute("SELECT id FROM leagues WHERE code='LGC1'").fetchone()["id"]
        db.execute(
            "UPDATE clubs SET country_id=?, league_id=?, is_real=0 WHERE league_id IS NULL",
            (country_id, league_id),
        )

    for career in db.execute("SELECT id, club_id, league_id, season_number FROM careers").fetchall():
        club = db.execute("SELECT league_id FROM clubs WHERE id=?", (career["club_id"],)).fetchone()
        league_id = career["league_id"] or (club["league_id"] if club else None)
        if league_id is None:
            continue
        db.execute("UPDATE careers SET league_id=? WHERE id=?", (league_id, career["id"]))
        db.execute("UPDATE fixtures SET league_id=? WHERE career_id=? AND league_id IS NULL", (league_id, career["id"]))
        db.execute("UPDATE standings SET league_id=?, season_number=? WHERE career_id=?", (league_id, career["season_number"], career["id"]))
        if db.execute("SELECT COUNT(*) AS n FROM world_memberships WHERE career_id=?", (career["id"],)).fetchone()["n"] == 0:
            initialize_world_memberships(db, career["id"], career["season_number"])


def initialize_world_memberships(db, career_id: int, season_number: int) -> None:
    rows = db.execute("SELECT id, league_id FROM clubs WHERE league_id IS NOT NULL").fetchall()
    db.executemany(
        "INSERT OR IGNORE INTO world_memberships(career_id, season_number, club_id, league_id) VALUES (?, ?, ?, ?)",
        [(career_id, season_number, row["id"], row["league_id"]) for row in rows],
    )


def nationality_country_code(nationality: str) -> str | None:
    return NATIONALITY_TO_COUNTRY_CODE.get(nationality.strip().lower())


def choose_starting_club(db, nationality: str, overall: int, seed: int | None = None):
    rng = random.Random(seed if seed is not None else f"{nationality}:{overall}")
    country_code = nationality_country_code(nationality)
    params: list[Any] = []
    where = ["c.is_real = 1"]
    if country_code in {"ENG", "ESP", "ITA", "GER", "FRA"}:
        where += ["co.code = ?", "l.tier = 2"]
        params.append(country_code)
    elif country_code:
        where += ["co.code = ?"]
        params.append(country_code)
    else:
        where += ["l.tier = 2", "l.fully_playable = 1"]
    rows = db.execute(
        f"""
        SELECT c.*, l.id AS selected_league_id, l.name AS league_name, l.reputation AS league_reputation,
               co.code AS country_code, co.name AS country_name
        FROM clubs c
        JOIN leagues l ON l.id=c.league_id
        JOIN countries co ON co.id=c.country_id
        WHERE {' AND '.join(where)}
        ORDER BY c.strength, c.reputation
        """,
        params,
    ).fetchall()
    if not rows:
        rows = db.execute(
            """
            SELECT c.*, l.id AS selected_league_id, l.name AS league_name, l.reputation AS league_reputation,
                   co.code AS country_code, co.name AS country_name
            FROM clubs c JOIN leagues l ON l.id=c.league_id JOIN countries co ON co.id=c.country_id
            WHERE l.tier=2 AND l.fully_playable=1 ORDER BY c.strength
            """
        ).fetchall()
    realistic = [row for row in rows if row["strength"] <= overall + 18 and row["reputation"] <= 78]
    pool = realistic or list(rows[: max(4, len(rows) // 2)])
    weights = [max(1.0, 90 - row["reputation"] + row["youth_rating"] * 0.15) for row in pool]
    return rng.choices(pool, weights=weights, k=1)[0]


def create_player_league_season(db, career_id: int, season_number: int, league_id: int) -> None:
    """Generate the active player's league only; the rest of the world is simulated in bulk."""
    club_rows = db.execute(
        """
        SELECT c.id FROM world_memberships wm
        JOIN clubs c ON c.id=wm.club_id
        WHERE wm.career_id=? AND wm.season_number=? AND wm.league_id=?
        ORDER BY c.id
        """,
        (career_id, season_number, league_id),
    ).fetchall()
    club_ids = [row["id"] for row in club_rows]
    if len(club_ids) < 2:
        raise ValueError("Active league does not contain enough clubs")
    db.execute("DELETE FROM fixtures WHERE career_id=? AND season_number=?", (career_id, season_number))
    db.execute("DELETE FROM standings WHERE career_id=?", (career_id,))
    db.executemany(
        "INSERT INTO standings(career_id, club_id, league_id, season_number) VALUES (?, ?, ?, ?)",
        [(career_id, club_id, league_id, season_number) for club_id in club_ids],
    )
    rounds = _round_robin(club_ids)
    for week, round_pairs in enumerate(rounds, start=1):
        db.executemany(
            """
            INSERT INTO fixtures(
                career_id, season_number, week, home_club_id, away_club_id,
                league_id, stage, round_label
            ) VALUES (?, ?, ?, ?, ?, ?, 'league', ?)
            """,
            [(career_id, season_number, week, home, away, league_id, f"Matchweek {week}") for home, away in round_pairs],
        )


def get_league_row(db, league_id: int):
    return db.execute(
        """
        SELECT l.*, co.name AS country_name, co.code AS country_code, co.confederation
        FROM leagues l JOIN countries co ON co.id=l.country_id WHERE l.id=?
        """,
        (league_id,),
    ).fetchone()


def get_world_overview(db, career_id: int, season_number: int) -> dict[str, Any]:
    countries = db.execute(
        """
        SELECT co.id, co.code, co.name, co.confederation,
               COUNT(DISTINCT l.id) AS league_count, COUNT(DISTINCT wm.club_id) AS club_count
        FROM countries co
        LEFT JOIN leagues l ON l.country_id=co.id
        LEFT JOIN world_memberships wm ON wm.league_id=l.id AND wm.career_id=? AND wm.season_number=?
        WHERE co.code <> 'LGC'
        GROUP BY co.id ORDER BY co.confederation, MAX(l.reputation) DESC, co.name
        """,
        (career_id, season_number),
    ).fetchall()
    leagues = db.execute(
        """
        SELECT l.*, co.name AS country_name, co.code AS country_code,
               COUNT(wm.club_id) AS current_clubs
        FROM leagues l JOIN countries co ON co.id=l.country_id
        LEFT JOIN world_memberships wm ON wm.league_id=l.id AND wm.career_id=? AND wm.season_number=?
        WHERE l.code <> 'LGC1'
        GROUP BY l.id ORDER BY l.fully_playable DESC, l.reputation DESC, co.name, l.tier
        """,
        (career_id, season_number),
    ).fetchall()
    competitions = db.execute(
        """
        SELECT cp.*, co.name AS country_name FROM competitions cp
        LEFT JOIN countries co ON co.id=cp.country_id
        ORDER BY cp.reputation DESC, cp.name
        """
    ).fetchall()
    return {"countries": countries, "leagues": leagues, "competitions": competitions}


def get_world_league(db, career_id: int, season_number: int, league_id: int) -> dict[str, Any] | None:
    league = get_league_row(db, league_id)
    if league is None:
        return None
    clubs = db.execute(
        """
        SELECT c.*, cu.development_rating AS academy_development
        FROM world_memberships wm JOIN clubs c ON c.id=wm.club_id
        LEFT JOIN club_units cu ON cu.club_id=c.id AND cu.unit_type='u18'
        WHERE wm.career_id=? AND wm.season_number=? AND wm.league_id=?
        ORDER BY c.reputation DESC, c.strength DESC, c.name
        """,
        (career_id, season_number, league_id),
    ).fetchall()
    return {"league": league, "clubs": clubs}


def simulate_virtual_table(db, career_id: int, season_number: int, league_id: int, rng: random.Random) -> list[dict[str, int]]:
    clubs = db.execute(
        """
        SELECT c.id, c.strength, c.reputation FROM world_memberships wm
        JOIN clubs c ON c.id=wm.club_id
        WHERE wm.career_id=? AND wm.season_number=? AND wm.league_id=?
        """,
        (career_id, season_number, league_id),
    ).fetchall()
    n = len(clubs)
    matches = max(0, (n - 1) * 2)
    rows = []
    for club in clubs:
        quality = club["strength"] * 0.75 + club["reputation"] * 0.25
        points_per_match = max(0.55, min(2.35, 1.22 + (quality - 65) / 35 + rng.uniform(-0.20, 0.20)))
        points = max(0, min(matches * 3, round(matches * points_per_match)))
        won = max(0, min(matches, round(points / 3 * rng.uniform(0.82, 1.02))))
        drawn = max(0, min(matches - won, points - won * 3))
        lost = max(0, matches - won - drawn)
        gf = max(5, round(matches * max(0.55, 1.25 + (quality - 65) / 28 + rng.uniform(-0.18, 0.18))))
        ga = max(5, round(matches * max(0.55, 1.30 - (quality - 65) / 35 + rng.uniform(-0.16, 0.18))))
        rows.append({"club_id": club["id"], "played": matches, "won": won, "drawn": drawn, "lost": lost, "goals_for": gf, "goals_against": ga, "points": points})
    rows.sort(key=lambda item: (item["points"], item["goals_for"] - item["goals_against"], item["goals_for"]), reverse=True)
    for position, row in enumerate(rows, start=1):
        row["position"] = position
    return rows


def _actual_active_table(db, career_id: int, league_id: int) -> list[dict[str, int]]:
    rows = db.execute(
        """
        SELECT club_id, played, won, drawn, lost, goals_for, goals_against, points
        FROM standings WHERE career_id=? AND league_id=?
        ORDER BY points DESC, (goals_for-goals_against) DESC, goals_for DESC
        """,
        (career_id, league_id),
    ).fetchall()
    return [{**dict(row), "position": index} for index, row in enumerate(rows, start=1)]


def resolve_world_season(db, career_id: int, season_number: int, active_league_id: int, seed: int) -> dict[str, Any]:
    """Freeze every league table and create next-season promotion/relegation memberships."""
    rng = random.Random(seed)
    leagues = db.execute("SELECT * FROM leagues WHERE code <> 'LGC1' ORDER BY country_id, tier").fetchall()
    tables: dict[int, list[dict[str, int]]] = {}
    for league in leagues:
        table = _actual_active_table(db, career_id, league["id"]) if league["id"] == active_league_id else []
        if not table:
            table = simulate_virtual_table(db, career_id, season_number, league["id"], rng)
        tables[league["id"]] = table
        for row in table:
            db.execute(
                """
                INSERT OR REPLACE INTO world_season_outcomes(
                    career_id, season_number, league_id, club_id, position, played, won, drawn, lost,
                    goals_for, goals_against, points, promoted, relegated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
                """,
                (career_id, season_number, league["id"], row["club_id"], row["position"], row["played"], row["won"], row["drawn"], row["lost"], row["goals_for"], row["goals_against"], row["points"]),
            )

    next_season = season_number + 1
    db.execute("DELETE FROM world_memberships WHERE career_id=? AND season_number=?", (career_id, next_season))
    current_memberships = db.execute(
        "SELECT club_id, league_id FROM world_memberships WHERE career_id=? AND season_number=?",
        (career_id, season_number),
    ).fetchall()
    next_membership = {row["club_id"]: row["league_id"] for row in current_memberships}

    by_country: dict[int, list[Any]] = defaultdict(list)
    for league in leagues:
        by_country[league["country_id"]].append(league)
    movement_log = []
    for country_leagues in by_country.values():
        country_leagues.sort(key=lambda row: row["tier"])
        for top, lower in zip(country_leagues, country_leagues[1:]):
            if top["tier"] + 1 != lower["tier"]:
                continue
            count = min(top["relegation_slots"], lower["promotion_slots"])
            if count <= 0:
                continue
            relegated = tables[top["id"]][-count:]
            promoted = tables[lower["id"]][:count]
            for row in relegated:
                next_membership[row["club_id"]] = lower["id"]
                db.execute("UPDATE world_season_outcomes SET relegated=1 WHERE career_id=? AND season_number=? AND league_id=? AND club_id=?", (career_id, season_number, top["id"], row["club_id"]))
            for row in promoted:
                next_membership[row["club_id"]] = top["id"]
                db.execute("UPDATE world_season_outcomes SET promoted=1 WHERE career_id=? AND season_number=? AND league_id=? AND club_id=?", (career_id, season_number, lower["id"], row["club_id"]))
            movement_log.append({"from": top["name"], "to": lower["name"], "relegated": [row["club_id"] for row in relegated], "promoted": [row["club_id"] for row in promoted]})

    db.executemany(
        "INSERT INTO world_memberships(career_id, season_number, club_id, league_id) VALUES (?, ?, ?, ?)",
        [(career_id, next_season, club_id, league_id) for club_id, league_id in next_membership.items()],
    )
    qualification_count = assign_continental_qualification(db, career_id, season_number, tables)
    return {"next_season": next_season, "movements": movement_log, "tables": tables, "qualification_count": qualification_count}


def award_player_of_month(db, career_id: int, season_number: int, current_week: int, league_id: int) -> str | None:
    if current_week < 4 or current_week % 4 != 0:
        return None
    start_week = current_week - 3
    reports = db.execute(
        """
        SELECT player_rating, player_goals, player_assists, player_motm, player_minutes
        FROM match_reports WHERE career_id=? AND season_number=? AND week BETWEEN ? AND ?
        ORDER BY week
        """,
        (career_id, season_number, start_week, current_week),
    ).fetchall()
    appeared = [row for row in reports if row["player_minutes"] > 0]
    if len(appeared) < 3:
        return None
    avg = sum(row["player_rating"] for row in appeared) / len(appeared)
    goals = sum(row["player_goals"] for row in appeared)
    assists = sum(row["player_assists"] for row in appeared)
    motm = sum(row["player_motm"] for row in appeared)
    score = avg + goals * 0.28 + assists * 0.20 + motm * 0.18
    if score < 7.55:
        return None
    evidence = {"weeks": [start_week, current_week], "average_rating": round(avg, 2), "goals": goals, "assists": assists, "motm": motm, "selection_score": round(score, 2)}
    db.execute(
        """
        INSERT OR IGNORE INTO career_awards(
            career_id, season_number, week, league_id, award_type, award_name, evidence_json
        ) VALUES (?, ?, ?, ?, 'monthly', 'Player of the Month', ?)
        """,
        (career_id, season_number, current_week, league_id, json.dumps(evidence, sort_keys=True)),
    )
    return "Player of the Month"


def record_motm_award(db, career_id: int, season_number: int, week: int, league_id: int, fixture_id: int, rating: float) -> None:
    db.execute(
        """
        INSERT OR IGNORE INTO career_awards(
            career_id, season_number, week, league_id, award_type, award_name, evidence_json
        ) VALUES (?, ?, ?, ?, 'match', 'Man of the Match', ?)
        """,
        (career_id, season_number, week, league_id, json.dumps({"fixture_id": fixture_id, "rating": rating}, sort_keys=True)),
    )


def record_season_awards(db, career, season_stats, league_position: int, league_reputation: int) -> list[str]:
    awards: list[str] = []
    avg = season_stats["average_rating"]
    if season_stats["appearances"] >= 10 and avg >= 7.35:
        awards.append("Club Player of the Season")
    if season_stats["appearances"] >= 14 and avg >= 7.65:
        awards.append("League Player of the Season")
    if season_stats["goals"] >= max(12, round(season_stats["appearances"] * 0.55)):
        awards.append("League Golden Boot")
    if season_stats["assists"] >= max(9, round(season_stats["appearances"] * 0.38)):
        awards.append("League Playmaker Award")
    if league_position == 1:
        awards.append("League Champion")
    ballon_score = (
        avg * 8 + season_stats["goals"] * 1.6 + season_stats["assists"] * 1.1
        + season_stats["motm"] * 1.8 + league_reputation * 0.18 + (10 if league_position == 1 else 0)
    )
    if season_stats["appearances"] >= 20 and ballon_score >= 105 and league_reputation >= 75:
        awards.append("Ballon d'Or")
    for award in awards:
        db.execute(
            """
            INSERT OR IGNORE INTO career_awards(
                career_id, season_number, week, league_id, award_type, award_name, evidence_json
            ) VALUES (?, ?, NULL, ?, 'season', ?, ?)
            """,
            (career["id"], career["season_number"], career["league_id"], award, json.dumps({"average_rating": avg, "goals": season_stats["goals"], "assists": season_stats["assists"], "league_position": league_position, "ballon_score": round(ballon_score, 2)}, sort_keys=True)),
        )
    return awards


def get_career_awards(db, career_id: int, limit: int = 100):
    return db.execute(
        """
        SELECT ca.*, l.name AS league_name, cp.name AS competition_name
        FROM career_awards ca
        LEFT JOIN leagues l ON l.id=ca.league_id
        LEFT JOIN competitions cp ON cp.id=ca.competition_id
        WHERE ca.career_id=? ORDER BY ca.season_number DESC, COALESCE(ca.week, 999) DESC, ca.id DESC LIMIT ?
        """,
        (career_id, limit),
    ).fetchall()


def _weighted_club_choice(rows, rng: random.Random):
    if not rows:
        return None
    weights = [max(1.0, (row["strength"] * 0.72 + row["reputation"] * 0.28) - 38) ** 2 for row in rows]
    return rng.choices(rows, weights=weights, k=1)[0]


def assign_continental_qualification(db, career_id: int, season_number: int, tables: dict[int, list[dict[str, int]]]) -> int:
    """Create next-season continental entries from frozen domestic league tables.

    This is intentionally rules-driven and conservative. It creates qualification
    records and world history; playable cup match calendars are a separate engine.
    """
    next_season = season_number + 1
    db.execute("DELETE FROM competition_entries WHERE career_id=? AND season_number=?", (career_id, next_season))
    competition_ids = {row["code"]: row["id"] for row in db.execute("SELECT id, code FROM competitions")}
    created = 0
    league_rows = db.execute(
        """
        SELECT l.*, c.confederation FROM leagues l
        JOIN countries c ON c.id=l.country_id
        WHERE l.tier=1 AND l.code <> 'LGC1'
        """
    ).fetchall()
    for league in league_rows:
        table = tables.get(league["id"], [])
        if not table:
            continue
        confed = league["confederation"]
        allocations: list[tuple[str, int, int]] = []
        if confed == "UEFA":
            # Simplified stable allocation for the game world. Stronger leagues
            # receive four UCL places; smaller UEFA leagues receive fewer.
            if league["reputation"] >= 85:
                allocations = [("UCL", 0, 4), ("UEL", 4, 2), ("UECL", 6, 1)]
            elif league["reputation"] >= 72:
                allocations = [("UCL", 0, 2), ("UEL", 2, 1), ("UECL", 3, 1)]
            else:
                allocations = [("UCL", 0, 1), ("UECL", 1, 1)]
        elif confed == "CONMEBOL":
            allocations = [("LIB", 0, 4), ("SUD", 4, 2)]
        elif confed == "CONCACAF":
            allocations = [("CCC", 0, 4)]
        elif confed == "AFC":
            allocations = [("ACL", 0, 3)]
        for competition_code, start, count in allocations:
            competition_id = competition_ids.get(competition_code)
            if competition_id is None:
                continue
            for row in table[start:start + count]:
                db.execute(
                    """
                    INSERT OR IGNORE INTO competition_entries(
                        career_id, season_number, competition_id, club_id,
                        qualification_source, status
                    ) VALUES (?, ?, ?, ?, ?, 'qualified')
                    """,
                    (career_id, next_season, competition_id, row["club_id"], f"{league['name']} position {row['position']}"),
                )
                created += 1
    return created


def simulate_background_honours(db, career_id: int, season_number: int, seed: int) -> list[dict[str, Any]]:
    """Resolve non-playable cup winners from the same seeded world state.

    Domestic, continental and international competition entities therefore build
    persistent history before their full fixture engines arrive.
    """
    rng = random.Random(seed ^ 0x5F3759DF)
    honours: list[dict[str, Any]] = []
    competitions = db.execute(
        """
        SELECT cp.*, co.code AS country_code FROM competitions cp
        LEFT JOIN countries co ON co.id=cp.country_id
        WHERE cp.competition_type IN ('domestic_cup','continental_club','super_cup','world_club')
        """
    ).fetchall()
    for competition in competitions:
        if competition["country_id"] is not None:
            candidates = db.execute(
                """
                SELECT DISTINCT c.id, c.name, c.strength, c.reputation
                FROM world_memberships wm JOIN clubs c ON c.id=wm.club_id
                WHERE wm.career_id=? AND wm.season_number=? AND c.country_id=?
                """,
                (career_id, season_number, competition["country_id"]),
            ).fetchall()
        elif competition["competition_type"] == "world_club" or competition["confederation"] == "FIFA":
            candidates = db.execute(
                """
                SELECT DISTINCT c.id, c.name, c.strength, c.reputation
                FROM world_memberships wm
                JOIN clubs c ON c.id=wm.club_id
                WHERE wm.career_id=? AND wm.season_number=? AND c.is_real=1
                """,
                (career_id, season_number),
            ).fetchall()
        else:
            candidates = db.execute(
                """
                SELECT DISTINCT c.id, c.name, c.strength, c.reputation
                FROM world_memberships wm
                JOIN clubs c ON c.id=wm.club_id
                JOIN countries co ON co.id=c.country_id
                WHERE wm.career_id=? AND wm.season_number=? AND co.confederation=?
                """,
                (career_id, season_number, competition["confederation"]),
            ).fetchall()
        if len(candidates) < 2:
            continue
        winner = _weighted_club_choice(candidates, rng)
        runner_candidates = [row for row in candidates if row["id"] != winner["id"]]
        runner = _weighted_club_choice(runner_candidates, rng)
        db.execute(
            """
            INSERT OR REPLACE INTO competition_honours(
                career_id, season_number, competition_id, winner_club_id,
                runner_up_club_id, notes
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (career_id, season_number, competition["id"], winner["id"], runner["id"], "Background world simulation; full cup fixture engine pending"),
        )
        honours.append({"competition": competition["name"], "winner": winner["name"], "runner_up": runner["name"]})
    return honours


def get_competition_entries(db, career_id: int, season_number: int):
    return db.execute(
        """
        SELECT ce.*, cp.name AS competition_name, cp.code AS competition_code,
               c.name AS club_name
        FROM competition_entries ce
        JOIN competitions cp ON cp.id=ce.competition_id
        JOIN clubs c ON c.id=ce.club_id
        WHERE ce.career_id=? AND ce.season_number=?
        ORDER BY cp.reputation DESC, cp.name, c.reputation DESC
        """,
        (career_id, season_number),
    ).fetchall()


def get_competition_honours(db, career_id: int, limit: int = 60):
    return db.execute(
        """
        SELECT ch.*, cp.name AS competition_name, cp.code AS competition_code,
               winner.name AS winner_name, runner.name AS runner_up_name
        FROM competition_honours ch
        JOIN competitions cp ON cp.id=ch.competition_id
        LEFT JOIN clubs winner ON winner.id=ch.winner_club_id
        LEFT JOIN clubs runner ON runner.id=ch.runner_up_club_id
        WHERE ch.career_id=?
        ORDER BY ch.season_number DESC, cp.reputation DESC, cp.name LIMIT ?
        """,
        (career_id, limit),
    ).fetchall()
