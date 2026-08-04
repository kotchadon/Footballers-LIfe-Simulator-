from __future__ import annotations

import json
import random
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone

from .db import get_db
from .engine import (
    POSITION_WEIGHTS,
    build_commentary_events,
    build_post_match_analysis,
    commentary_to_text,
    calculate_overall,
    create_starting_attributes,
    player_selection_probability,
    simulate_player_performance,
    simulate_score,
)
from .world import (
    award_player_of_month,
    choose_starting_club,
    create_player_league_season,
    get_career_awards as world_get_career_awards,
    get_league_row,
    get_world_league as world_get_league,
    get_world_overview as world_get_overview,
    initialize_world_memberships,
    record_motm_award,
    record_season_awards,
    resolve_world_season,
    simulate_background_honours,
    get_competition_entries as world_get_competition_entries,
    get_competition_honours as world_get_competition_honours,
)

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

TRAINING_FOCUS = {
    "balanced": {
        "label": "Balanced development",
        "attribute": None,
        "weekly_xp": 8,
        "description": "A broad plan that follows the strengths of your position.",
    },
    "pace": {
        "label": "Explosive pace",
        "attribute": "pace",
        "weekly_xp": 12,
        "description": "Acceleration, movement and repeated sprint work.",
    },
    "shooting": {
        "label": "Finishing lab",
        "attribute": "shooting",
        "weekly_xp": 12,
        "description": "Finishing, shot selection and composure around goal.",
    },
    "passing": {
        "label": "Playmaking",
        "attribute": "passing",
        "weekly_xp": 12,
        "description": "Vision, passing range and decision-making under pressure.",
    },
    "dribbling": {
        "label": "Ball mastery",
        "attribute": "dribbling",
        "weekly_xp": 12,
        "description": "Close control, turning and carrying the ball through traffic.",
    },
    "defending": {
        "label": "Defensive craft",
        "attribute": "defending",
        "weekly_xp": 12,
        "description": "Positioning, anticipation, tackling and recovery defending.",
    },
    "physical": {
        "label": "Athletic base",
        "attribute": "physical",
        "weekly_xp": 12,
        "description": "Strength, balance, stamina and resilience in duels.",
    },
    "recovery": {
        "label": "Recovery week",
        "attribute": None,
        "weekly_xp": 0,
        "description": "No development load; prioritises fitness and morale before the match.",
    },
}


def seed_clubs():
    """Compatibility shim: world data is seeded during app initialization."""
    return None


def round_robin(team_ids):
    teams = list(team_ids)
    if len(teams) % 2:
        teams.append(None)
    rounds = []
    for round_index in range(len(teams) - 1):
        fixtures = []
        for index in range(len(teams) // 2):
            first, second = teams[index], teams[-1 - index]
            if first is not None and second is not None:
                fixtures.append((first, second) if (round_index + index) % 2 == 0 else (second, first))
        rounds.append(fixtures)
        teams = [teams[0], teams[-1], *teams[1:-1]]
    return rounds + [[(away, home) for home, away in fixtures] for fixtures in rounds]


def _create_season_world(career_id, season_number, league_id=None):
    db = get_db()
    if league_id is None:
        career = db.execute("SELECT league_id FROM careers WHERE id=?", (career_id,)).fetchone()
        if career is None or career["league_id"] is None:
            raise ValueError("Career league is not configured")
        league_id = career["league_id"]
    create_player_league_season(db, career_id, season_number, league_id)


def create_career(player_name, nationality, position):
    db = get_db()
    rng = random.Random()
    attributes = create_starting_attributes(position, rng)
    overall = calculate_overall(attributes, position, potential=88)
    starting_club = choose_starting_club(db, nationality, overall)
    pathway = "senior_development"
    squad_level = "first_team" if overall >= starting_club["strength"] - 10 else "reserve_bridge"
    manager_trust = max(20, min(48, 52 - (starting_club["strength"] - overall)))
    wage = max(250, round((starting_club["reputation"] * 8 + overall * 5) / 25) * 25)

    cursor = db.execute(
        """
        INSERT INTO careers(
            player_name, nationality, position, overall, club_id, league_id,
            squad_level, manager_trust, pathway_status, wage
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            player_name.strip(), nationality.strip(), position, overall,
            starting_club["id"], starting_club["selected_league_id"], squad_level,
            manager_trust, pathway, wage,
        ),
    )
    career_id = cursor.lastrowid
    db.execute("INSERT INTO player_stats(career_id) VALUES (?)", (career_id,))
    db.execute(
        """
        INSERT INTO player_attributes(
            career_id, pace, shooting, passing, dribbling, defending, physical
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (career_id, attributes["pace"], attributes["shooting"], attributes["passing"], attributes["dribbling"], attributes["defending"], attributes["physical"]),
    )
    db.execute(
        "INSERT INTO season_player_stats(career_id, season_number, season_label, club_id) VALUES (?, 1, '2026/27', ?)",
        (career_id, starting_club["id"]),
    )
    db.execute(
        "INSERT INTO club_history(career_id, club_id, joined_season, reason) VALUES (?, ?, 1, ?)",
        (career_id, starting_club["id"], f"Signed through {starting_club['league_name']} development pathway"),
    )
    initialize_world_memberships(db, career_id, 1)
    _create_season_world(career_id, 1, starting_club["selected_league_id"])
    db.commit()
    return career_id

def get_active_career():
    return get_db().execute(
        """
        SELECT careers.*, clubs.name AS club_name, clubs.short_name,
               clubs.strength AS club_strength, clubs.reputation AS club_reputation,
               clubs.youth_rating, clubs.reserve_rating,
               leagues.name AS league_name, leagues.code AS league_code,
               leagues.tier AS league_tier, leagues.reputation AS league_reputation,
               countries.name AS country_name, countries.code AS country_code,
               pa.pace, pa.shooting, pa.passing, pa.dribbling, pa.defending, pa.physical
        FROM careers
        JOIN clubs ON clubs.id = careers.club_id
        LEFT JOIN leagues ON leagues.id = careers.league_id
        LEFT JOIN countries ON countries.id = leagues.country_id
        JOIN player_attributes pa ON pa.career_id = careers.id
        ORDER BY careers.id DESC LIMIT 1
        """
    ).fetchone()


def get_standings(career_id):
    return get_db().execute(
        """
        SELECT clubs.name, clubs.short_name, clubs.strength, clubs.reputation, standings.*,
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
        SELECT fixtures.*, home.name AS home_name, away.name AS away_name,
               leagues.name AS league_name, leagues.code AS league_code
        FROM fixtures
        JOIN clubs home ON home.id = fixtures.home_club_id
        JOIN clubs away ON away.id = fixtures.away_club_id
        LEFT JOIN leagues ON leagues.id = fixtures.league_id
        WHERE fixtures.career_id = ? AND fixtures.season_number = ? AND fixtures.week >= ?
          AND fixtures.played = 0 AND fixtures.league_id = ?
          AND (fixtures.home_club_id = ? OR fixtures.away_club_id = ?)
        ORDER BY fixtures.week, fixtures.id
        LIMIT 1
        """,
        (
            career["id"],
            career["season_number"],
            career["current_week"],
            career["league_id"],
            career["club_id"],
            career["club_id"],
        ),
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


def _selection_status(career, rng, fitness=None):
    if career["injured_weeks"] > 0:
        return "injured", 0
    if career["suspended_matches"] > 0:
        return "suspended", 0

    effective_fitness = career["fitness"] if fitness is None else fitness
    probability = player_selection_probability(
        career["overall"], career["club_strength"], effective_fitness, career["morale"]
    )
    trust = career["manager_trust"] if "manager_trust" in career.keys() else 35
    probability += (trust - 35) / 140
    if "squad_level" in career.keys() and career["squad_level"] == "reserve_bridge":
        probability -= 0.10
    probability = max(0.04, min(0.92, probability))
    roll = rng.random()
    if roll < probability:
        return "starter", 90
    if roll < min(0.94, probability + 0.32):
        return "substitute", rng.randint(15, 35)
    return "bench", 0


def _increase_attribute_for_xp(db, career, rng, preferred_focus="balanced"):
    preferred = TRAINING_FOCUS.get(preferred_focus, TRAINING_FOCUS["balanced"])["attribute"]
    if preferred and rng.random() < 0.72:
        attribute_name = preferred
    else:
        weights = POSITION_WEIGHTS.get(career["position"], POSITION_WEIGHTS["CM"])
        weighted_names = []
        for name, weight in weights.items():
            weighted_names.extend([name] * max(1, round(weight * 20)))
        attribute_name = rng.choice(weighted_names)

    db.execute(
        f"UPDATE player_attributes SET {attribute_name} = MIN(99, {attribute_name} + 1) WHERE career_id = ?",
        (career["id"],),
    )
    return attribute_name


def _apply_xp(db, career, xp_gain, rng, preferred_focus="balanced"):
    xp = career["xp"] + max(0, xp_gain)
    upgrades = []
    levels = 0
    while xp >= 100 and career["overall"] + levels < career["potential"]:
        xp -= 100
        levels += 1
        upgrades.append(_increase_attribute_for_xp(db, career, rng, preferred_focus))

    attributes = db.execute(
        "SELECT pace, shooting, passing, dribbling, defending, physical FROM player_attributes WHERE career_id = ?",
        (career["id"],),
    ).fetchone()
    overall = calculate_overall(dict(attributes), career["position"], career["potential"])
    db.execute("UPDATE careers SET xp = ?, overall = ? WHERE id = ?", (xp, overall, career["id"]))
    return {"xp": xp, "overall": overall, "upgrades": upgrades}


def _update_stats_table(db, table, career, selection_status, minutes, performance, win, draw, loss):
    if table == "player_stats":
        where_clause = "career_id = ?"
        where_values = (career["id"],)
    else:
        where_clause = "career_id = ? AND season_number = ?"
        where_values = (career["id"], career["season_number"])

    db.execute(
        f"""
        UPDATE {table}
        SET appearances = appearances + 1,
            starts = starts + ?,
            sub_appearances = sub_appearances + ?,
            minutes = minutes + ?,
            goals = goals + ?, assists = assists + ?,
            yellow_cards = yellow_cards + ?, red_cards = red_cards + ?,
            motm = motm + ?, rating_total = rating_total + ?,
            wins = wins + ?, draws = draws + ?, losses = losses + ?
        WHERE {where_clause}
        """,
        (
            int(selection_status == "starter"),
            int(selection_status == "substitute"),
            minutes,
            performance["goals"],
            performance["assists"],
            performance["yellow_cards"],
            performance["red_cards"],
            int(performance["motm"]),
            performance["rating"],
            win,
            draw,
            loss,
            *where_values,
        ),
    )


def _zero_metrics():
    return {
        "shots": 0,
        "shots_on_target": 0,
        "shot_accuracy": 0.0,
        "xg": 0.0,
        "key_passes": 0,
        "big_chances_created": 0,
        "xa": 0.0,
        "passes_attempted": 0,
        "passes_completed": 0,
        "pass_accuracy": 0.0,
        "dribbles_attempted": 0,
        "dribbles_completed": 0,
        "dribble_success": 0.0,
        "tackles_attempted": 0,
        "tackles_won": 0,
        "tackle_success": 0.0,
        "duels": 0,
        "duels_won": 0,
        "duel_win_rate": 0.0,
        "touches": 0,
        "turnovers": 0,
        "fouls_committed": 0,
        "progressive_actions": 0,
        "schema_version": 1,
    }


def _choose_development_attribute(position, focus, rng):
    preferred = TRAINING_FOCUS.get(focus, TRAINING_FOCUS["balanced"])["attribute"]
    if preferred and rng.random() < 0.72:
        return preferred
    weights = POSITION_WEIGHTS.get(position, POSITION_WEIGHTS["CM"])
    names = list(weights)
    chances = [weights[name] for name in names]
    return rng.choices(names, weights=chances, k=1)[0]


def _plan_development(career, xp_gain, preferred_focus, seed):
    """Pure, deterministic development plan stored inside the sealed match snapshot."""
    rng = random.Random(seed)
    attributes = {
        name: int(career[name])
        for name in ("pace", "shooting", "passing", "dribbling", "defending", "physical")
    }
    xp = int(career["xp"]) + max(0, int(xp_gain))
    upgrades = []
    while xp >= 100:
        current_overall = calculate_overall(attributes, career["position"], career["potential"])
        if current_overall >= career["potential"]:
            xp = min(xp, 99)
            break
        xp -= 100
        attribute = _choose_development_attribute(career["position"], preferred_focus, rng)
        attributes[attribute] = min(99, attributes[attribute] + 1)
        upgrades.append(attribute)
    overall = calculate_overall(attributes, career["position"], career["potential"])
    return {"xp": xp, "overall": overall, "attributes": attributes, "upgrades": upgrades}


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_dump(payload):
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def _json_load(payload):
    return json.loads(payload) if isinstance(payload, str) else payload


def get_active_match_session(career_id):
    return get_db().execute(
        """
        SELECT * FROM match_sessions
        WHERE career_id = ? AND status = 'prepared'
        ORDER BY id DESC LIMIT 1
        """,
        (career_id,),
    ).fetchone()


def _build_match_snapshot(career, fixtures, seed):
    rng = random.Random(seed)
    simulation_start_week = int(career.get("simulation_start_week", career["current_week"]))
    target_week = max(fixture["week"] for fixture in fixtures if career["club_id"] in (fixture["home_club_id"], fixture["away_club_id"]))
    simulation_end_week = int(career.get("simulation_end_week", target_week))
    pre_match_weeks = max(1, target_week - simulation_start_week + 1)
    elapsed_weeks = max(pre_match_weeks, simulation_end_week - simulation_start_week + 1)
    idle_weeks = pre_match_weeks - 1
    training_focus = career["training_focus"] if career["training_focus"] in TRAINING_FOCUS else "balanced"
    training_plan = TRAINING_FOCUS[training_focus]
    recovery_per_week = rng.randint(13, 17) if training_focus == "recovery" else rng.randint(8, 12)
    recovery_gain = recovery_per_week * pre_match_weeks
    pre_match_fitness = min(100, career["fitness"] + recovery_gain)
    week_results = []
    player_fixture = None
    performance = None
    selection_status = "bench"
    minutes = 0
    player_team_is_home = False
    team_goals = 0
    opponent_goals = 0

    for fixture in fixtures:
        result = simulate_score(fixture["home_strength"], fixture["away_strength"], rng)
        result_row = {
            "fixture_id": fixture["id"],
            "week": fixture["week"],
            "home_club_id": fixture["home_club_id"],
            "away_club_id": fixture["away_club_id"],
            "home_name": fixture["home_name"],
            "away_name": fixture["away_name"],
            "home_goals": result.home_goals,
            "away_goals": result.away_goals,
        }
        week_results.append(result_row)
        if career["club_id"] not in (fixture["home_club_id"], fixture["away_club_id"]):
            continue
        if fixture["week"] != target_week:
            continue

        player_fixture = result_row
        selection_career = dict(career)
        selection_career["injured_weeks"] = max(0, career["injured_weeks"] - idle_weeks)
        selection_status, minutes = _selection_status(selection_career, rng, fitness=pre_match_fitness)
        appeared = selection_status in {"starter", "substitute"}
        player_team_is_home = career["club_id"] == fixture["home_club_id"]
        team_goals = result.home_goals if player_team_is_home else result.away_goals
        opponent_goals = result.away_goals if player_team_is_home else result.home_goals

        if appeared:
            performance = simulate_player_performance(
                player_name=career["player_name"],
                position=career["position"],
                overall=career["overall"],
                fitness=pre_match_fitness,
                morale=career["morale"],
                team_goals=team_goals,
                opponent_goals=opponent_goals,
                minutes=minutes,
                selection_status=selection_status,
                physical=career["physical"],
                defending=career["defending"],
                rng=rng,
            )
        else:
            reason = {
                "injured": f"{career['player_name']} misses the match through injury.",
                "suspended": f"{career['player_name']} watches from the stands while serving a suspension.",
                "bench": f"{career['player_name']} is named on the bench but is not introduced.",
            }[selection_status]
            metrics = _zero_metrics()
            events = build_commentary_events(
                career["player_name"], 0, 0, 0.0, team_goals, opponent_goals,
                selection_status, 0, 0, 0, False, rng, metrics=metrics,
            )
            events.insert(1, {
                "minute": 1,
                "text": reason,
                "kind": "selection_note",
                "metadata": {"side": "player"},
                "sequence": 1,
                "score": {"player": 0, "opponent": 0},
            })
            for sequence, event in enumerate(events):
                event["sequence"] = sequence
            performance = {
                "goals": 0,
                "assists": 0,
                "yellow_cards": 0,
                "red_cards": 0,
                "injured": False,
                "injury_weeks": 0,
                "rating": 0.0,
                "motm": False,
                "metrics": metrics,
                "events": events,
                "commentary": commentary_to_text(events),
            }

    if player_fixture is None or performance is None:
        raise ValueError("Player fixture was not found for the current matchweek")

    win = int(team_goals > opponent_goals)
    draw = int(team_goals == opponent_goals)
    loss = int(team_goals < opponent_goals)
    if selection_status == "starter":
        match_load = rng.randint(7, 11)
    elif selection_status == "substitute":
        match_load = rng.randint(3, 5)
    else:
        match_load = 0
    fitness_after = max(45, min(100, pre_match_fitness - match_load))

    selection_morale = {"starter": 2, "substitute": 0, "bench": -2, "injured": -1, "suspended": -3}[selection_status]
    morale_change = rng.randint(-1, 2) + selection_morale + (2 if win else -2 if loss else 0)
    if training_focus == "recovery":
        morale_change += 2
    reputation_gain = performance["goals"] * 2 + performance["assists"] + int(performance["motm"])

    appeared = selection_status in {"starter", "substitute"}
    match_xp = 0
    if appeared:
        match_xp = max(2, round(performance["rating"] * 1.5)) + performance["goals"] * 5 + performance["assists"] * 3
    training_xp = 0
    effective_injury_weeks = max(0, career["injured_weeks"] - idle_weeks)
    if effective_injury_weeks == 0 and training_focus != "recovery":
        training_xp = training_plan["weekly_xp"] * elapsed_weeks
        if appeared and performance["rating"] >= 7.5:
            training_xp += 2

    injury_weeks = effective_injury_weeks
    if selection_status == "injured":
        injury_weeks = max(0, injury_weeks - 1)
    suspension_matches = max(0, career["suspended_matches"] - 1) if selection_status == "suspended" else career["suspended_matches"]
    if performance["injured"]:
        injury_weeks = max(injury_weeks, performance["injury_weeks"])
    if performance["red_cards"]:
        suspension_matches = max(suspension_matches, rng.randint(1, 3))
    yellow_accumulation = career["yellow_card_accumulation"] + performance["yellow_cards"]
    if yellow_accumulation >= 5:
        suspension_matches = max(suspension_matches, 1)
        yellow_accumulation -= 5

    development_seed = rng.getrandbits(63)
    development = _plan_development(
        career,
        match_xp + training_xp,
        training_focus,
        development_seed,
    )
    if development["upgrades"]:
        upgraded = ", ".join(name.title() for name in development["upgrades"])
        development_summary = f"Development breakthrough: {upgraded} +1. XP now {development['xp']}/100."
    elif training_focus == "recovery":
        development_summary = f"Recovery week completed. Fitness restored to {fitness_after}%."
    else:
        development_summary = (
            f"{training_plan['label']} added {training_xp} training XP; "
            f"match performance added {match_xp} XP. Progress: {development['xp']}/100."
        )

    weekly_income = career["wage"] * elapsed_weeks
    bonus = performance["goals"] * 75 + performance["assists"] * 40 + int(performance["motm"]) * 100
    max_week = max(fixture["week"] for fixture in fixtures)
    # max_week above is current week only; actual season max is resolved during commit.

    return {
        "schema_version": 1,
        "seed": seed,
        "career": {
            "id": career["id"],
            "season_number": career["season_number"],
            "season_label": career["season_label"],
            "week": target_week,
            "start_week": simulation_start_week,
            "elapsed_weeks": elapsed_weeks,
            "end_week": simulation_end_week,
            "club_id": career["club_id"],
            "league_id": career["league_id"],
            "player_name": career["player_name"],
            "position": career["position"],
            "training_focus": training_focus,
        },
        "fixture": {
            **player_fixture,
            "player_team_is_home": player_team_is_home,
            "team_goals": team_goals,
            "opponent_goals": opponent_goals,
        },
        "week_results": week_results,
        "performance": {
            **performance,
            "selection_status": selection_status,
            "minutes": minutes,
            "fitness_before": pre_match_fitness,
            "fitness_after": fitness_after,
        },
        "post_match": {
            "appeared": appeared,
            "win": win,
            "draw": draw,
            "loss": loss,
            "morale_change": morale_change,
            "reputation_gain": reputation_gain,
            "injury_weeks": injury_weeks,
            "suspension_matches": suspension_matches,
            "yellow_accumulation": yellow_accumulation,
            "match_xp": match_xp,
            "training_xp": training_xp,
            "development": development,
            "development_seed": development_seed,
            "development_summary": development_summary,
            "weekly_income": weekly_income,
            "bonus": bonus,
        },
    }


def prepare_next_match(career_id, seed=None):
    """Create one sealed simulation without mutating career or league state."""
    db = get_db()
    existing = get_active_match_session(career_id)
    if existing is not None:
        return existing

    career = db.execute(
        """
        SELECT careers.*, clubs.strength AS club_strength,
               pa.pace, pa.shooting, pa.passing, pa.dribbling, pa.defending, pa.physical
        FROM careers
        JOIN clubs ON clubs.id = careers.club_id
        JOIN player_attributes pa ON pa.career_id = careers.id
        WHERE careers.id = ?
        """,
        (career_id,),
    ).fetchone()
    if career is None:
        raise ValueError("Career not found")

    target = db.execute(
        """
        SELECT MIN(week) AS target_week FROM fixtures
        WHERE career_id=? AND season_number=? AND league_id=? AND played=0
          AND week>=? AND (home_club_id=? OR away_club_id=?)
        """,
        (career_id, career["season_number"], career["league_id"], career["current_week"], career["club_id"], career["club_id"]),
    ).fetchone()
    if target is None or target["target_week"] is None:
        return None
    target_week = target["target_week"]
    later_player_fixture = db.execute(
        """
        SELECT MIN(week) AS next_week FROM fixtures
        WHERE career_id=? AND season_number=? AND league_id=? AND played=0
          AND week>? AND (home_club_id=? OR away_club_id=?)
        """,
        (career_id, career["season_number"], career["league_id"], target_week, career["club_id"], career["club_id"]),
    ).fetchone()["next_week"]
    if later_player_fixture is None:
        end_week = db.execute(
            "SELECT MAX(week) AS max_week FROM fixtures WHERE career_id=? AND season_number=? AND league_id=?",
            (career_id, career["season_number"], career["league_id"]),
        ).fetchone()["max_week"]
    else:
        end_week = target_week
    fixtures = db.execute(
        """
        SELECT f.*, h.strength AS home_strength, a.strength AS away_strength,
               h.name AS home_name, a.name AS away_name
        FROM fixtures f
        JOIN clubs h ON h.id=f.home_club_id
        JOIN clubs a ON a.id=f.away_club_id
        WHERE f.career_id=? AND f.season_number=? AND f.week BETWEEN ? AND ?
          AND f.played=0 AND f.league_id=?
        ORDER BY f.week, f.id
        """,
        (career_id, career["season_number"], career["current_week"], end_week, career["league_id"]),
    ).fetchall()
    if not fixtures:
        return None

    career_payload = dict(career)
    career_payload["simulation_start_week"] = career["current_week"]
    career_payload["simulation_end_week"] = end_week
    seed_value = int(seed) if seed is not None else secrets.randbits(63)
    snapshot = _build_match_snapshot(career_payload, fixtures, seed_value)
    public_id = uuid.uuid4().hex
    report_json = _json_dump({"status": "pending"})
    try:
        db.execute(
            """
            INSERT INTO match_sessions(
                public_id, career_id, season_number, week, player_fixture_id, seed,
                status, revealed_event_count, event_count, simulation_json, report_json
            ) VALUES (?, ?, ?, ?, ?, ?, 'prepared', 0, ?, ?, ?)
            """,
            (
                public_id,
                career_id,
                career["season_number"],
                target_week,
                snapshot["fixture"]["fixture_id"],
                seed_value,
                len(snapshot["performance"]["events"]),
                _json_dump(snapshot),
                report_json,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        existing = get_active_match_session(career_id)
        if existing is None:
            raise
        return existing
    return db.execute("SELECT * FROM match_sessions WHERE public_id = ?", (public_id,)).fetchone()


def get_match_session_view(public_id, career_id):
    row = get_db().execute(
        "SELECT * FROM match_sessions WHERE public_id = ? AND career_id = ?",
        (public_id, career_id),
    ).fetchone()
    if row is None:
        return None
    snapshot = _json_load(row["simulation_json"])
    fixture = snapshot["fixture"]
    performance = snapshot["performance"]
    return {
        "public_id": row["public_id"],
        "status": row["status"],
        "event_count": row["event_count"],
        "revealed_event_count": row["revealed_event_count"],
        "home_name": fixture["home_name"],
        "away_name": fixture["away_name"],
        "player_team_is_home": fixture["player_team_is_home"],
        "selection_status": performance["selection_status"],
        "player_name": snapshot["career"]["player_name"],
        "position": snapshot["career"]["position"],
        "season_label": snapshot["career"]["season_label"],
        "week": snapshot["career"]["week"],
        "league_id": snapshot["career"].get("league_id"),
    }


def advance_match_session(public_id, career_id, cursor):
    db = get_db()
    row = db.execute(
        "SELECT * FROM match_sessions WHERE public_id = ? AND career_id = ?",
        (public_id, career_id),
    ).fetchone()
    if row is None:
        return False, "Match session not found.", None
    if row["status"] == "completed":
        return True, "Match already completed.", {"completed": True, "cursor": row["event_count"]}

    snapshot = _json_load(row["simulation_json"])
    events = snapshot["performance"]["events"]
    try:
        cursor = int(cursor)
    except (TypeError, ValueError):
        return False, "Invalid replay cursor.", None
    if cursor < 0 or cursor >= len(events):
        return False, "Replay cursor is outside the event ledger.", None
    revealed = int(row["revealed_event_count"])
    if cursor > revealed:
        return False, "Replay cursor skipped an unrevealed event.", None
    if cursor == revealed:
        db.execute(
            "UPDATE match_sessions SET revealed_event_count = ? WHERE id = ? AND revealed_event_count = ?",
            (revealed + 1, row["id"], revealed),
        )
        db.commit()
    event = events[cursor]
    return True, "Event revealed.", {
        "completed": False,
        "event": event,
        "cursor": cursor + 1,
        "event_count": len(events),
        "has_more": cursor + 1 < len(events),
    }


def _build_final_analysis(snapshot):
    fixture = snapshot["fixture"]
    performance = snapshot["performance"]
    return build_post_match_analysis(
        player_name=snapshot["career"]["player_name"],
        position=snapshot["career"]["position"],
        selection_status=performance["selection_status"],
        minutes=performance["minutes"],
        goals=performance["goals"],
        assists=performance["assists"],
        rating=performance["rating"],
        motm=performance["motm"],
        yellow_cards=performance["yellow_cards"],
        red_cards=performance["red_cards"],
        injured=performance["injured"],
        team_goals=fixture["team_goals"],
        opponent_goals=fixture["opponent_goals"],
        metrics=performance["metrics"],
        events=performance["events"],
    )


def _completion_payload(snapshot, analysis, session_status="completed"):
    fixture = snapshot["fixture"]
    performance = snapshot["performance"]
    post_match = snapshot["post_match"]
    return {
        "status": session_status,
        "final_score": {"home": fixture["home_goals"], "away": fixture["away_goals"]},
        "player_team_is_home": fixture["player_team_is_home"],
        "week_results": snapshot["week_results"],
        "remaining_events": performance["events"],
        "report": {
            "selection_status": performance["selection_status"],
            "minutes": performance["minutes"],
            "goals": performance["goals"],
            "assists": performance["assists"],
            "yellow_cards": performance["yellow_cards"],
            "red_cards": performance["red_cards"],
            "injured": performance["injured"],
            "rating": performance["rating"],
            "motm": performance["motm"],
            "fitness_before": performance["fitness_before"],
            "fitness_after": performance["fitness_after"],
            "development_summary": post_match["development_summary"],
            "metrics": performance["metrics"],
            "analysis": analysis,
        },
    }


def complete_match_session(public_id, career_id, allow_skip=False):
    """Commit a sealed simulation exactly once.

    The transaction is idempotent: retries after a lost network response return the
    same final payload without duplicating stats, money, cards, injuries or XP.
    """
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    try:
        row = db.execute(
            "SELECT * FROM match_sessions WHERE public_id = ? AND career_id = ?",
            (public_id, career_id),
        ).fetchone()
        if row is None:
            db.rollback()
            return False, "Match session not found.", None
        snapshot = _json_load(row["simulation_json"])
        if row["status"] == "completed":
            stored = _json_load(row["report_json"])
            analysis = stored.get("analysis") if isinstance(stored, dict) else None
            if not analysis:
                analysis = _build_final_analysis(snapshot)
            db.commit()
            return True, "Match already completed.", _completion_payload(snapshot, analysis)
        if not allow_skip and row["revealed_event_count"] < row["event_count"]:
            db.rollback()
            return False, "The replay has not reached full time.", None

        career = db.execute(
            "SELECT * FROM careers WHERE id = ?",
            (career_id,),
        ).fetchone()
        expected = snapshot["career"]
        if career is None or career["season_number"] != expected["season_number"] or career["current_week"] != expected.get("start_week", expected["week"]):
            db.rollback()
            return False, "Career state changed after this match was prepared.", None

        for result in snapshot["week_results"]:
            cursor = db.execute(
                """
                UPDATE fixtures SET played = 1, home_goals = ?, away_goals = ?
                WHERE id = ? AND career_id = ? AND played = 0
                """,
                (result["home_goals"], result["away_goals"], result["fixture_id"], career_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError(f"Fixture {result['fixture_id']} was already committed")
            update_standing(career_id, result["home_club_id"], result["home_goals"], result["away_goals"])
            update_standing(career_id, result["away_club_id"], result["away_goals"], result["home_goals"])

        performance = snapshot["performance"]
        post_match = snapshot["post_match"]
        selection_status = performance["selection_status"]
        if post_match["appeared"]:
            _update_stats_table(
                db, "player_stats", career, selection_status, performance["minutes"],
                performance, post_match["win"], post_match["draw"], post_match["loss"],
            )
            _update_stats_table(
                db, "season_player_stats", career, selection_status, performance["minutes"],
                performance, post_match["win"], post_match["draw"], post_match["loss"],
            )
        elif selection_status == "injured":
            db.execute(
                "UPDATE player_stats SET matches_missed_injury = matches_missed_injury + 1 WHERE career_id = ?",
                (career_id,),
            )
        elif selection_status == "suspended":
            db.execute(
                "UPDATE player_stats SET matches_missed_suspension = matches_missed_suspension + 1 WHERE career_id = ?",
                (career_id,),
            )
        if performance["injured"]:
            db.execute("UPDATE player_stats SET injuries = injuries + 1 WHERE career_id = ?", (career_id,))

        development = post_match["development"]
        attrs = development["attributes"]
        db.execute(
            """
            UPDATE player_attributes
            SET pace = ?, shooting = ?, passing = ?, dribbling = ?, defending = ?, physical = ?
            WHERE career_id = ?
            """,
            (attrs["pace"], attrs["shooting"], attrs["passing"], attrs["dribbling"], attrs["defending"], attrs["physical"], career_id),
        )
        db.execute(
            """
            UPDATE careers
            SET fitness = ?, morale = MIN(100, MAX(15, morale + ?)),
                reputation = MIN(100, reputation + ?), money = money + ?,
                injured_weeks = ?, suspended_matches = ?, yellow_card_accumulation = ?,
                xp = ?, overall = ?,
                manager_trust = MIN(100, MAX(5, manager_trust + ?)),
                squad_level = CASE
                    WHEN squad_level = 'reserve_bridge' AND ? >= 58 THEN 'first_team'
                    ELSE squad_level END
            WHERE id = ?
            """,
            (
                performance["fitness_after"], post_match["morale_change"], post_match["reputation_gain"],
                post_match["weekly_income"] + post_match["bonus"], post_match["injury_weeks"],
                post_match["suspension_matches"], post_match["yellow_accumulation"],
                development["xp"], development["overall"],
                (3 if performance["rating"] >= 7.5 else 1 if performance["rating"] >= 6.5 else -2 if post_match["appeared"] else -1),
                development["overall"], career_id,
            ),
        )

        fixture = snapshot["fixture"]
        final_analysis = _build_final_analysis(snapshot)
        report_record = {
            "status": "completed",
            "analysis": final_analysis,
            "generated_at": _utc_now(),
            "source": "sealed_event_ledger",
        }
        db.execute(
            """
            INSERT INTO match_reports(
                career_id, season_number, week, fixture_id, player_started, selection_status,
                player_minutes, player_goals, player_assists, player_yellow_cards,
                player_red_cards, player_injured, player_rating, player_motm, commentary,
                development_summary, fitness_before, fitness_after, session_id,
                events_json, metrics_json, analysis_json, finalized_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                career_id, expected["season_number"], expected["week"], fixture["fixture_id"],
                int(selection_status == "starter"), selection_status, performance["minutes"],
                performance["goals"], performance["assists"], performance["yellow_cards"],
                performance["red_cards"], int(performance["injured"]), performance["rating"],
                int(performance["motm"]), performance["commentary"], post_match["development_summary"],
                performance["fitness_before"], performance["fitness_after"], row["id"],
                _json_dump(performance["events"]), _json_dump(performance["metrics"]),
                _json_dump(final_analysis), _utc_now(),
            ),
        )
        if performance["motm"]:
            record_motm_award(
                db, career_id, expected["season_number"], expected["week"],
                expected.get("league_id") or career["league_id"], fixture["fixture_id"], performance["rating"],
            )
        award_player_of_month(
            db, career_id, expected["season_number"], expected["week"],
            expected.get("league_id") or career["league_id"],
        )

        db.execute(
            """
            INSERT INTO finance_transactions(career_id, season_number, week, category, amount, description)
            VALUES (?, ?, ?, 'Wages', ?, ?)
            """,
            (career_id, expected["season_number"], expected["week"], post_match["weekly_income"], f"Weekly wage from {fixture['home_name'] if fixture['player_team_is_home'] else fixture['away_name']}"),
        )
        if post_match["bonus"]:
            db.execute(
                """
                INSERT INTO finance_transactions(career_id, season_number, week, category, amount, description)
                VALUES (?, ?, ?, 'Match bonus', ?, 'Goals, assists and performance bonus')
                """,
                (career_id, expected["season_number"], expected["week"], post_match["bonus"]),
            )

        max_week = db.execute(
            "SELECT MAX(week) AS max_week FROM fixtures WHERE career_id = ? AND season_number = ? AND league_id = ?",
            (career_id, expected["season_number"], expected.get("league_id") or career["league_id"]),
        ).fetchone()["max_week"]
        next_week = min(expected.get("end_week", expected["week"]) + 1, max_week + 1)
        db.execute(
            "UPDATE careers SET current_week = ?, weekly_action_used = 0 WHERE id = ?",
            (next_week, career_id),
        )
        db.execute(
            """
            UPDATE match_sessions
            SET status = 'completed', revealed_event_count = event_count,
                report_json = ?, completed_at = ?
            WHERE id = ? AND status = 'prepared'
            """,
            (_json_dump(report_record), _utc_now(), row["id"]),
        )
        db.commit()
        return True, "Match completed.", _completion_payload(snapshot, final_analysis)
    except Exception:
        db.rollback()
        raise


def play_next_week(career_id, seed=None):
    """Backward-compatible headless helper used by tests and season simulation.

    Browser gameplay uses prepare_next_match + event replay + complete_match_session.
    """
    session = prepare_next_match(career_id, seed=seed)
    if session is None:
        return None
    success, message, payload = complete_match_session(session["public_id"], career_id, allow_skip=True)
    if not success:
        raise RuntimeError(message)
    snapshot = _json_load(session["simulation_json"])
    performance = snapshot["performance"]
    fixture = snapshot["fixture"]
    return {
        "fixture_id": fixture["fixture_id"],
        "home_name": fixture["home_name"],
        "away_name": fixture["away_name"],
        "home_goals": fixture["home_goals"],
        "away_goals": fixture["away_goals"],
        "selection_status": performance["selection_status"],
        "minutes": performance["minutes"],
        "started": performance["selection_status"] == "starter",
        "player_team_is_home": fixture["player_team_is_home"],
        "development_summary": snapshot["post_match"]["development_summary"],
        "fitness_before": performance["fitness_before"],
        "fitness_after": performance["fitness_after"],
        **{key: performance[key] for key in (
            "goals", "assists", "yellow_cards", "red_cards", "injured", "injury_weeks",
            "rating", "motm", "metrics", "events", "commentary"
        )},
        "analysis": payload["report"]["analysis"],
    }

def get_training_plan(career_id):
    career = get_db().execute(
        "SELECT training_focus, xp, fitness, injured_weeks FROM careers WHERE id = ?",
        (career_id,),
    ).fetchone()
    if career is None:
        return None
    focus = career["training_focus"] if career["training_focus"] in TRAINING_FOCUS else "balanced"
    return {
        "focus": focus,
        "xp": career["xp"],
        "fitness": career["fitness"],
        "injured_weeks": career["injured_weeks"],
        **TRAINING_FOCUS[focus],
    }


def set_training_focus(career_id, focus):
    if focus not in TRAINING_FOCUS:
        return False, "Unknown training plan.", None
    db = get_db()
    career = db.execute("SELECT id FROM careers WHERE id = ?", (career_id,)).fetchone()
    if career is None:
        return False, "Career not found.", None
    if get_active_match_session(career_id) is not None:
        return False, "Finish or skip the active match before changing the training plan.", get_training_plan(career_id)
    db.execute(
        "UPDATE careers SET training_focus = ?, weekly_action_used = 0 WHERE id = ?",
        (focus, career_id),
    )
    db.commit()
    plan = get_training_plan(career_id)
    return True, f"Training plan set to {plan['label']}.", plan


def recover_player(career_id):
    success, message, _plan = set_training_focus(career_id, "recovery")
    return success, message


def train_player(career_id, focus):
    success, message, _plan = set_training_focus(career_id, focus)
    return success, message


def get_stats(career_id):
    return get_db().execute(
        """
        SELECT *, CASE WHEN appearances = 0 THEN 0 ELSE ROUND(rating_total / appearances, 2) END AS average_rating
        FROM player_stats WHERE career_id = ?
        """,
        (career_id,),
    ).fetchone()


def get_season_stats(career_id, season_number):
    return get_db().execute(
        """
        SELECT *, CASE WHEN appearances = 0 THEN 0 ELSE ROUND(rating_total / appearances, 2) END AS average_rating
        FROM season_player_stats WHERE career_id = ? AND season_number = ?
        """,
        (career_id, season_number),
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


def get_week_results(career_id, season_number, week):
    return get_db().execute(
        """
        SELECT f.*, h.name AS home_name, a.name AS away_name
        FROM fixtures f
        JOIN clubs h ON h.id = f.home_club_id
        JOIN clubs a ON a.id = f.away_club_id
        WHERE f.career_id = ? AND f.season_number = ? AND f.week = ? AND f.played = 1
        ORDER BY f.id
        """,
        (career_id, season_number, week),
    ).fetchall()


def season_is_complete(career):
    max_week_row = get_db().execute(
        "SELECT MAX(week) AS max_week FROM fixtures WHERE career_id = ? AND season_number = ? AND league_id = ?",
        (career["id"], career["season_number"], career["league_id"]),
    ).fetchone()
    return max_week_row["max_week"] is not None and career["current_week"] > max_week_row["max_week"]


def _next_season_label(label):
    start = int(label.split("/")[0]) + 1
    return f"{start}/{str(start + 1)[-2:]}"


def _generate_transfer_offers(db, career, season_stats, rng, target_season):
    """Create cross-league offers from clubs that actually exist next season."""
    if season_stats["appearances"] < 4:
        return 0

    current_club = db.execute(
        "SELECT c.*, l.reputation AS league_reputation FROM clubs c JOIN leagues l ON l.id=? WHERE c.id=?",
        (career["league_id"], career["club_id"]),
    ).fetchone()
    performance_score = (
        career["overall"]
        + career["reputation"] * 0.18
        + season_stats["average_rating"] * 1.8
        + min(12, (season_stats["goals"] + season_stats["assists"]) * 0.45)
    )
    rows = db.execute(
        """
        SELECT c.*, wm.league_id AS destination_league_id,
               l.name AS league_name, l.reputation AS league_reputation,
               co.name AS country_name
        FROM world_memberships wm
        JOIN clubs c ON c.id=wm.club_id
        JOIN leagues l ON l.id=wm.league_id
        JOIN countries co ON co.id=l.country_id
        WHERE wm.career_id=? AND wm.season_number=? AND c.id<>?
        ORDER BY l.reputation, c.strength
        """,
        (career["id"], target_season, career["club_id"]),
    ).fetchall()
    candidates = []
    for club in rows:
        upward = club["strength"] >= current_club["strength"] - 2
        attainable = club["strength"] <= performance_score + 8
        league_jump_ok = club["league_reputation"] <= current_club["league_reputation"] + max(8, career["reputation"] // 4)
        if upward and attainable and league_jump_ok:
            candidates.append(club)
    if not candidates:
        candidates = [row for row in rows if row["strength"] > current_club["strength"]][:8]

    # Diversity: no more than one offer per league, maximum three offers.
    rng.shuffle(candidates)
    selected = []
    used_leagues = set()
    for club in sorted(candidates, key=lambda row: (row["league_reputation"], row["strength"]), reverse=True):
        if club["destination_league_id"] in used_leagues:
            continue
        selected.append(club)
        used_leagues.add(club["destination_league_id"])
        if len(selected) == 3:
            break

    for club in selected:
        wage = max(
            career["wage"] + 100,
            round((club["strength"] * 11 + club["league_reputation"] * 7 + career["overall"] * 5) / 50) * 50,
        )
        signing_bonus = wage * rng.randint(4, 8)
        db.execute(
            """
            INSERT INTO transfer_offers(
                career_id, season_number, from_club_id, to_club_id,
                wage, signing_bonus, to_league_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (career["id"], target_season, career["club_id"], club["id"], wage, signing_bonus, club["destination_league_id"]),
        )
    return len(selected)


def finalize_season(career_id, seed=None):
    seed_value = int(seed) if seed is not None else secrets.randbits(63)
    rng = random.Random(seed_value)
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    try:
        career = db.execute(
            """
            SELECT careers.*, clubs.strength AS club_strength,
                   leagues.name AS league_name, leagues.reputation AS league_reputation
            FROM careers
            JOIN clubs ON clubs.id=careers.club_id
            JOIN leagues ON leagues.id=careers.league_id
            WHERE careers.id=?
            """,
            (career_id,),
        ).fetchone()
        if career is None:
            db.rollback()
            return False, "Career not found."
        if get_active_match_session(career_id) is not None:
            db.rollback()
            return False, "Finish the active match before finalising the season."
        if not season_is_complete(career):
            db.rollback()
            return False, "The season is not complete yet."
        if db.execute(
            "SELECT 1 FROM season_history WHERE career_id=? AND season_number=?",
            (career_id, career["season_number"]),
        ).fetchone():
            db.rollback()
            return False, "This season has already been finalised."

        standings = get_standings(career_id)
        position = next(index for index, row in enumerate(standings, 1) if row["club_id"] == career["club_id"])
        club_row = next(row for row in standings if row["club_id"] == career["club_id"])
        season_stats = get_season_stats(career_id, career["season_number"])
        awards = record_season_awards(db, career, season_stats, position, career["league_reputation"])

        db.execute(
            """
            INSERT INTO season_history(
                career_id, season_number, season_label, club_id, league_id,
                league_position, league_points, appearances, goals, assists,
                average_rating, awards
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                career_id, career["season_number"], career["season_label"], career["club_id"],
                career["league_id"], position, club_row["points"], season_stats["appearances"],
                season_stats["goals"], season_stats["assists"], season_stats["average_rating"],
                ", ".join(awards),
            ),
        )

        prize = max(500, round(career["league_reputation"] * (len(standings) - position + 1) * 7.5))
        if position == 1:
            prize += career["league_reputation"] * 40
        prize += len(awards) * max(300, career["league_reputation"] * 6)
        db.execute(
            """
            INSERT INTO finance_transactions(career_id, season_number, week, category, amount, description)
            VALUES (?, ?, ?, 'Season rewards', ?, ?)
            """,
            (career_id, career["season_number"], career["current_week"], prize,
             f"{career['league_name']} finish: {position}; awards: {', '.join(awards) or 'none'}"),
        )

        world_result = resolve_world_season(
            db, career_id, career["season_number"], career["league_id"], seed_value
        )
        simulate_background_honours(db, career_id, career["season_number"], seed_value)
        next_number = career["season_number"] + 1
        next_label = _next_season_label(career["season_label"])
        membership = db.execute(
            "SELECT league_id FROM world_memberships WHERE career_id=? AND season_number=? AND club_id=?",
            (career_id, next_number, career["club_id"]),
        ).fetchone()
        next_league_id = membership["league_id"] if membership else career["league_id"]

        offer_count = _generate_transfer_offers(db, career, season_stats, rng, next_number)
        db.execute(
            """
            UPDATE careers
            SET age=age+1, season_number=?, season_label=?, current_week=1,
                league_id=?, weekly_action_used=0, fitness=MIN(100, fitness+20),
                morale=MIN(100, morale+?), money=money+?,
                manager_trust=MIN(100, MAX(10, manager_trust+?))
            WHERE id=?
            """,
            (next_number, next_label, next_league_id, 8 if position <= 3 else 3, prize,
             5 if position <= 4 else -2, career_id),
        )
        db.execute(
            """
            INSERT INTO season_player_stats(career_id, season_number, season_label, club_id)
            VALUES (?, ?, ?, ?)
            """,
            (career_id, next_number, next_label, career["club_id"]),
        )
        _create_season_world(career_id, next_number, next_league_id)
        db.commit()

        movement = ""
        if next_league_id != career["league_id"]:
            next_league = get_league_row(db, next_league_id)
            movement = f" Your club moves to {next_league['name']}."
        summary = (
            f"{career['season_label']} complete: {position} in {career['league_name']}, "
            f"earned ${prize:,}. {world_result['qualification_count']} continental places recorded."
            f"{movement} {offer_count} transfer offer(s) generated."
        )
        if awards:
            summary += f" Awards: {', '.join(awards)}."
        return True, summary
    except Exception:
        db.rollback()
        raise


def get_pending_transfer_offers(career_id):
    return get_db().execute(
        """
        SELECT transfer_offers.*, source.name AS from_name, destination.name AS to_name,
               destination.strength AS to_strength, destination.reputation AS to_reputation,
               l.name AS to_league_name, l.reputation AS to_league_reputation,
               co.name AS to_country_name
        FROM transfer_offers
        JOIN clubs source ON source.id=transfer_offers.from_club_id
        JOIN clubs destination ON destination.id=transfer_offers.to_club_id
        LEFT JOIN leagues l ON l.id=transfer_offers.to_league_id
        LEFT JOIN countries co ON co.id=l.country_id
        WHERE transfer_offers.career_id=? AND transfer_offers.status='pending'
        ORDER BY l.reputation DESC, destination.strength DESC
        """,
        (career_id,),
    ).fetchall()


def accept_transfer_offer(career_id, offer_id):
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    try:
        offer = db.execute(
            "SELECT * FROM transfer_offers WHERE id=? AND career_id=? AND status='pending'",
            (offer_id, career_id),
        ).fetchone()
        if offer is None:
            db.rollback()
            return False, "Transfer offer is no longer available."
        career = db.execute("SELECT * FROM careers WHERE id=?", (career_id,)).fetchone()
        if get_active_match_session(career_id) is not None or career["current_week"] != 1:
            db.rollback()
            return False, "Transfers can only be completed before the new season begins."
        club = db.execute(
            """
            SELECT c.*, l.name AS league_name, l.id AS destination_league_id
            FROM clubs c JOIN leagues l ON l.id=? WHERE c.id=?
            """,
            (offer["to_league_id"], offer["to_club_id"]),
        ).fetchone()
        membership = db.execute(
            """
            SELECT 1 FROM world_memberships
            WHERE career_id=? AND season_number=? AND club_id=? AND league_id=?
            """,
            (career_id, career["season_number"], offer["to_club_id"], offer["to_league_id"]),
        ).fetchone()
        if membership is None:
            db.rollback()
            return False, "The destination club is not registered in that league this season."

        db.execute("UPDATE transfer_offers SET status='accepted' WHERE id=?", (offer_id,))
        db.execute("UPDATE transfer_offers SET status='declined' WHERE career_id=? AND id<>? AND status='pending'", (career_id, offer_id))
        db.execute("UPDATE club_history SET left_season=? WHERE career_id=? AND left_season IS NULL", (career["season_number"], career_id))
        db.execute(
            "INSERT INTO club_history(career_id, club_id, joined_season, reason) VALUES (?, ?, ?, 'Transfer')",
            (career_id, offer["to_club_id"], career["season_number"]),
        )
        squad_level = "first_team" if career["overall"] >= club["strength"] - 9 else "reserve_bridge"
        trust = max(18, min(55, 50 - (club["strength"] - career["overall"])))
        db.execute(
            """
            UPDATE careers SET club_id=?, league_id=?, wage=?, money=money+?,
                morale=MIN(100, morale+8), squad_level=?, manager_trust=?
            WHERE id=?
            """,
            (offer["to_club_id"], offer["to_league_id"], offer["wage"], offer["signing_bonus"], squad_level, trust, career_id),
        )
        db.execute(
            "UPDATE season_player_stats SET club_id=? WHERE career_id=? AND season_number=?",
            (offer["to_club_id"], career_id, career["season_number"]),
        )
        # The active match calendar follows the destination league after transfer.
        _create_season_world(career_id, career["season_number"], offer["to_league_id"])
        db.execute(
            """
            INSERT INTO finance_transactions(career_id, season_number, week, category, amount, description)
            VALUES (?, ?, ?, 'Signing bonus', ?, ?)
            """,
            (career_id, career["season_number"], career["current_week"], offer["signing_bonus"], f"Signed for {club['name']} in {club['league_name']}"),
        )
        db.commit()
        return True, f"Transfer complete: {club['name']} ({club['league_name']}) on ${offer['wage']:,} per week."
    except Exception:
        db.rollback()
        raise
def decline_transfer_offer(career_id, offer_id):
    db = get_db()
    cursor = db.execute(
        "UPDATE transfer_offers SET status = 'declined' WHERE id = ? AND career_id = ? AND status = 'pending'",
        (offer_id, career_id),
    )
    db.commit()
    return cursor.rowcount > 0


def get_season_history(career_id):
    return get_db().execute(
        """
        SELECT season_history.*, clubs.name AS club_name, leagues.name AS league_name,
               countries.name AS country_name
        FROM season_history
        JOIN clubs ON clubs.id=season_history.club_id
        LEFT JOIN leagues ON leagues.id=season_history.league_id
        LEFT JOIN countries ON countries.id=leagues.country_id
        WHERE season_history.career_id=? ORDER BY season_number DESC
        """,
        (career_id,),
    ).fetchall()


def get_club_history(career_id):
    return get_db().execute(
        """
        SELECT club_history.*, clubs.name AS club_name
        FROM club_history JOIN clubs ON clubs.id = club_history.club_id
        WHERE club_history.career_id = ? ORDER BY joined_season DESC, club_history.id DESC
        """,
        (career_id,),
    ).fetchall()


def get_finances(career_id, limit=20):
    return get_db().execute(
        """
        SELECT * FROM finance_transactions
        WHERE career_id = ? ORDER BY id DESC LIMIT ?
        """,
        (career_id, limit),
    ).fetchall()


def get_current_league(career):
    if career is None or career["league_id"] is None:
        return None
    return get_league_row(get_db(), career["league_id"])


def get_world_overview(career_id):
    career = get_db().execute("SELECT season_number FROM careers WHERE id=?", (career_id,)).fetchone()
    if career is None:
        return {"countries": [], "leagues": [], "competitions": []}
    return world_get_overview(get_db(), career_id, career["season_number"])


def get_world_league(career_id, league_id):
    career = get_db().execute("SELECT season_number FROM careers WHERE id=?", (career_id,)).fetchone()
    if career is None:
        return None
    return world_get_league(get_db(), career_id, career["season_number"], league_id)


def get_career_awards(career_id, limit=100):
    return world_get_career_awards(get_db(), career_id, limit)


def get_competition_entries(career_id):
    career = get_db().execute("SELECT season_number FROM careers WHERE id=?", (career_id,)).fetchone()
    if career is None:
        return []
    return world_get_competition_entries(get_db(), career_id, career["season_number"])


def get_competition_honours(career_id, limit=60):
    return world_get_competition_honours(get_db(), career_id, limit)
