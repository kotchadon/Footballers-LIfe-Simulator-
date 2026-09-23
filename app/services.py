from __future__ import annotations

import json
import random
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone

from .db import get_db
from .progression import ATTRIBUTES, apply_attribute_xp, match_development_xp, training_development_xp, upgrade_cost
from .match_visuals import build_visual_plan, visual_event_metadata
from .calendar_engine import generate_season_calendar, get_calendar, get_week_context
from .economy import (
    accept_endorsement as economy_accept_endorsement,
    buy_investment as economy_buy_investment,
    buy_property as economy_buy_property,
    decline_endorsement as economy_decline_endorsement,
    ensure_financial_profile,
    get_financial_dashboard as economy_get_financial_dashboard,
    get_selected_player_programme as economy_get_selected_player_programme,
    place_virtual_wager as economy_place_virtual_wager,
    process_weekly_finances,
    sell_investment as economy_sell_investment,
    take_offseason_action as economy_take_offseason_action,
)
from .international import get_international_summary as international_get_summary, process_international_week
from .transfer_market import (
    expire_market_offers,
    generate_transfer_market,
    get_market_dashboard as transfer_get_market_dashboard,
    request_agent_search as transfer_request_agent_search,
)
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
            career_id, pace, shooting, passing, dribbling, defending, physical,
            legacy_xp_migrated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
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
    generate_season_calendar(db, career_id, 1, "2026/27", starting_club["selected_league_id"])
    db.execute(
        "UPDATE careers SET calendar_week=4, season_phase='preseason', market_value=? WHERE id=?",
        (max(50_000, overall * overall * 38), career_id),
    )
    db.execute("INSERT OR IGNORE INTO international_player_stats(career_id) VALUES (?)", (career_id,))
    ensure_financial_profile(db, career_id)
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
               pa.pace, pa.shooting, pa.passing, pa.dribbling, pa.defending, pa.physical,
               pa.pace_xp, pa.shooting_xp, pa.passing_xp,
               pa.dribbling_xp, pa.defending_xp, pa.physical_xp
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


def _week_has_settled_match(db, career):
    """A week's training is included only in its first settled club match."""
    return db.execute(
        """
        SELECT 1 FROM match_sessions ms
        JOIN fixtures f ON f.id=ms.player_fixture_id
        WHERE ms.career_id=? AND ms.season_number=? AND ms.status='completed'
          AND COALESCE(f.calendar_week,f.week)=? LIMIT 1
        """,
        (career["id"], career["season_number"], career["calendar_week"]),
    ).fetchone() is not None


def _build_match_snapshot(career, fixtures, seed):
    rng = random.Random(seed)
    simulation_start_week = int(career.get("simulation_start_week", career["current_week"]))
    target_week = max(fixture["week"] for fixture in fixtures if career["club_id"] in (fixture["home_club_id"], fixture["away_club_id"]))
    simulation_end_week = int(career.get("simulation_end_week", target_week))
    # Calendar advancement now handles rest, salary and non-match weeks.
    # A sealed match therefore represents exactly one fixture, even when the
    # league uses midweek rounds in the same calendar week.
    pre_match_weeks = 1
    elapsed_weeks = 1
    idle_weeks = 0
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
            "calendar_week": fixture["calendar_week"] if "calendar_week" in fixture.keys() else fixture["week"],
            "kickoff_date": fixture["kickoff_date"] if "kickoff_date" in fixture.keys() else None,
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
    effective_injury_weeks = max(0, career["injured_weeks"] - idle_weeks)
    performance["minutes"] = minutes
    match_xp = match_development_xp(performance)
    training_xp = training_development_xp(
        focus=training_focus, position=career["position"],
        season_phase=career["season_phase"], minutes=minutes,
        unavailable_injured=effective_injury_weeks > 0,
    )
    if career.get("training_already_awarded", False):
        training_xp = dict.fromkeys(ATTRIBUTES, 0)

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

    attributes_before = {name: int(career[name]) for name in ATTRIBUTES}
    meters_before = {name: int(career[f"{name}_xp"]) for name in ATTRIBUTES}
    total_xp = {name: match_xp[name] + training_xp[name] for name in ATTRIBUTES}
    result = apply_attribute_xp(
        attributes=attributes_before, meters=meters_before, gains=total_xp,
        position=career["position"], potential=career["potential"],
    ) if any(total_xp.values()) else {
        "attributes": dict(attributes_before), "meters": dict(meters_before),
        "overall": career["overall"], "upgrades": [],
    }
    development = {
        "schema_version": 2,
        "match_xp": match_xp, "training_xp": training_xp, "total_xp": total_xp,
        "attributes_before": attributes_before, "meters_before": meters_before,
        "attributes": result["attributes"], "meters_after": result["meters"],
        "overall_before": career["overall"], "overall": result["overall"],
        "potential_before": career["potential"], "upgrades": result["upgrades"],
    }
    labels = dict(zip(ATTRIBUTES, ("PAC", "SHO", "PAS", "DRI", "DEF", "PHY")))
    def xp_text(gains):
        return " · ".join(f"{labels[name]} +{gains[name]} XP" for name in ATTRIBUTES if gains[name]) or "0 XP"
    development_summary = f"Match development: {xp_text(match_xp)}. Training: {xp_text(training_xp)}."
    if development["upgrades"]:
        transitions = " · ".join(
            f"{labels[item['attribute']]} {item['from']} → {item['to']}" for item in development["upgrades"]
        )
        development_summary += f" Development breakthrough: {transitions}."

    weekly_income = 0  # Salary is processed once per calendar week by the finance engine.
    bonus = performance["goals"] * 75 + performance["assists"] * 40 + int(performance["motm"]) * 100
    max_week = max(fixture["week"] for fixture in fixtures)
    # max_week above is current week only; actual season max is resolved during commit.

    snapshot = {
        "schema_version": 1,
        "seed": seed,
        "career": {
            "id": career["id"],
            "season_number": career["season_number"],
            "season_label": career["season_label"],
            "week": target_week,
            "calendar_week": player_fixture.get("calendar_week", career.get("calendar_week", target_week)),
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
            "development_summary": development_summary,
            "weekly_income": weekly_income,
            "bonus": bonus,
        },
    }
    snapshot["visual"] = build_visual_plan(snapshot, seed)
    return snapshot


def prepare_next_match(career_id, seed=None):
    """Create one sealed simulation without mutating career or league state."""
    db = get_db()
    existing = get_active_match_session(career_id)
    if existing is not None:
        return existing

    career = db.execute(
        """
        SELECT careers.*, clubs.strength AS club_strength,
               pa.pace, pa.shooting, pa.passing, pa.dribbling, pa.defending, pa.physical,
               pa.pace_xp, pa.shooting_xp, pa.passing_xp, pa.dribbling_xp, pa.defending_xp, pa.physical_xp
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
          AND week>=? AND COALESCE(calendar_week, week)<=?
          AND (home_club_id=? OR away_club_id=?)
        """,
        (career_id, career["season_number"], career["league_id"], career["current_week"], career["calendar_week"], career["club_id"], career["club_id"]),
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
    career_payload["training_already_awarded"] = _week_has_settled_match(db, career)
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



def get_match_visual_plan(public_id, career_id):
    row = get_db().execute(
        "SELECT seed, simulation_json FROM match_sessions WHERE public_id = ? AND career_id = ?",
        (public_id, career_id),
    ).fetchone()
    if row is None:
        return None
    snapshot = json.loads(row["simulation_json"])
    plan = snapshot.get("visual")
    if not isinstance(plan, dict):
        plan = build_visual_plan(snapshot, int(row["seed"]))
    return plan



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
        "calendar_week": snapshot["career"].get("calendar_week"),
        "kickoff_date": fixture.get("kickoff_date"),
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
    event = dict(events[cursor])
    event_sequence = int(
        event.get("sequence", cursor)
    )
    event["visual"] = visual_event_metadata(
        snapshot,
        event,
        event_sequence,
        seed=int(row["seed"]),
    )
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
        if (
            career is None
            or career["season_number"] != expected["season_number"]
            or career["current_week"] != expected.get("start_week", expected["week"])
            or career["calendar_week"] != expected.get("calendar_week", career["calendar_week"])
        ):
            db.rollback()
            return False, "Career state changed after this match was prepared.", None

        development = snapshot["post_match"]["development"]
        current_attributes = db.execute(
            "SELECT * FROM player_attributes WHERE career_id=?", (career_id,),
        ).fetchone()
        if development.get("schema_version") == 2 and (
            current_attributes is None
            or any(current_attributes[name] != development["attributes_before"][name] for name in ATTRIBUTES)
            or any(current_attributes[f"{name}_xp"] != development["meters_before"][name] for name in ATTRIBUTES)
            or career["overall"] != development["overall_before"]
            or career["potential"] != development["potential_before"]
        ):
            db.rollback()
            return False, "Player development changed after this match was prepared.", None

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
        if development.get("schema_version") == 2:
            meters = development["meters_after"]
        else:
            # Finish legacy prepared matches without rerolling their sealed result.
            # Migrate only their unspent global remainder, once, in this transaction.
            meters = {name: current_attributes[f"{name}_xp"] for name in ATTRIBUTES}
            focus = expected.get("training_focus", "balanced")
            if focus not in ATTRIBUTES:
                weights = POSITION_WEIGHTS.get(expected["position"], POSITION_WEIGHTS["CM"])
                focus = max(ATTRIBUTES, key=lambda name: weights[name])
            meters[focus] += max(0, int(development.get("xp", 0)))
        db.execute(
            """
            UPDATE player_attributes
            SET pace=?,shooting=?,passing=?,dribbling=?,defending=?,physical=?,
                pace_xp=?,shooting_xp=?,passing_xp=?,dribbling_xp=?,defending_xp=?,physical_xp=?
            WHERE career_id=?
            """,
            (*[attrs[name] for name in ATTRIBUTES], *[meters[name] for name in ATTRIBUTES], career_id),
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
                0, development["overall"],
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

        if post_match["bonus"]:
            db.execute(
                """
                INSERT INTO finance_transactions(career_id, season_number, week, calendar_week, category, amount, description)
                VALUES (?, ?, ?, ?, 'Match bonus', ?, 'Goals, assists and performance bonus')
                """,
                (career_id, expected["season_number"], expected["week"], expected.get("calendar_week"), post_match["bonus"]),
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
    """Headless helper that advances free calendar weeks to the next club match.

    Browser gameplay never jumps time automatically. Test and bulk-simulation
    callers may use this helper to process salary, recovery and international
    windows until the next playable fixture is reached.
    """
    for offset in range(60):
        career = get_active_career()
        if career is None or career["id"] != career_id:
            return None
        context = get_week_context(get_db(), career)
        if context["can_play"]:
            break
        success, _message, _data = advance_calendar_week(career_id, seed=(int(seed or 0) + offset + 7919))
        if not success:
            return None
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
    """Present persisted progress and a no-match estimate, never a sealed result."""
    db = get_db()
    career = db.execute(
        """
        SELECT c.*, pa.pace, pa.shooting, pa.passing, pa.dribbling, pa.defending, pa.physical,
               pa.pace_xp, pa.shooting_xp, pa.passing_xp, pa.dribbling_xp, pa.defending_xp, pa.physical_xp
        FROM careers c JOIN player_attributes pa ON pa.career_id=c.id
        WHERE c.id=?
        """,
        (career_id,),
    ).fetchone()
    if career is None:
        return None
    focus = career["training_focus"] if career["training_focus"] in TRAINING_FOCUS else "balanced"
    attributes = {}
    for name in ATTRIBUTES:
        value, xp = career[name], career[f"{name}_xp"]
        cost = upgrade_cost(value, career["overall"], career["potential"])
        capped = value >= 99 or career["overall"] >= career["potential"]
        attributes[name] = {
            "value": value, "xp": xp, "cost": cost,
            "percent": max(0, min(100, xp * 100 // cost)),
            "capped": capped, "next_value": None if capped else value + 1,
        }
    settled = _week_has_settled_match(db, career)
    preview = dict.fromkeys(ATTRIBUTES, 0) if settled else training_development_xp(
        focus=focus, position=career["position"], season_phase=career["season_phase"],
        minutes=0, unavailable_injured=career["injured_weeks"] > 0,
    )
    if settled:
        status, note = "settled", "This week's training has already been awarded."
    elif career["injured_weeks"] > 0:
        status, note = "injured", "Injury recovery: no training XP this week."
    elif focus == "recovery":
        status, note = "recovery", "Recovery improves fitness and stress; no training XP."
    else:
        status = "estimate"
        note = "No-match estimate. Match minutes reduce training XP; match-action XP is earned separately."
        if career["season_phase"] == "preseason":
            note += " Includes the preseason training bonus."
    return {
        "focus": focus, "label": TRAINING_FOCUS[focus]["label"],
        "description": TRAINING_FOCUS[focus]["description"],
        "fitness": career["fitness"], "injured_weeks": career["injured_weeks"],
        "attributes": attributes, "weekly_preview": preview,
        "preview_status": status, "preview_note": note,
        "locked": get_active_match_session(career_id) is not None,
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
    return generate_transfer_market(db, career, season_stats, rng, target_season)


def finalize_season(career_id, seed=None):
    """Close the competitive league season but keep the off-season playable.

    V5 jumped immediately into a new season. V6 separates league closure from
    the four-week close season so transfers, international finals, recovery and
    financial decisions can happen before the next pre-season begins.
    """
    seed_value = int(seed) if seed is not None else secrets.randbits(63)
    rng = random.Random(seed_value)
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    try:
        career = db.execute(
            """
            SELECT careers.*, clubs.strength AS club_strength, clubs.name AS club_name,
                   leagues.name AS league_name, leagues.reputation AS league_reputation
            FROM careers JOIN clubs ON clubs.id=careers.club_id
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
            return False, "Finish the active match before closing the season."
        if career["season_phase"] == "offseason":
            db.rollback()
            return False, "The league season is already closed. Advance through the off-season."
        if not season_is_complete(career):
            db.rollback()
            return False, "The league schedule is not complete yet."
        if db.execute(
            "SELECT 1 FROM season_history WHERE career_id=? AND season_number=?",
            (career_id, career["season_number"]),
        ).fetchone():
            db.rollback()
            return False, "This season has already been recorded."

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
            INSERT INTO finance_transactions(
                career_id, season_number, week, calendar_week, category, amount, description
            ) VALUES (?, ?, ?, ?, 'Season rewards', ?, ?)
            """,
            (
                career_id, career["season_number"], career["current_week"], career["calendar_week"], prize,
                f"{career['league_name']} finish: {position}; awards: {', '.join(awards) or 'none'}",
            ),
        )
        world_result = resolve_world_season(db, career_id, career["season_number"], career["league_id"], seed_value)
        simulate_background_honours(db, career_id, career["season_number"], seed_value)
        target_season = career["season_number"] + 1
        offer_count = generate_transfer_market(db, career, season_stats, rng, target_season)
        db.execute(
            """
            UPDATE careers SET season_phase='offseason', calendar_week=MAX(calendar_week,49),
                fitness=MIN(100,fitness+8), morale=MIN(100,morale+?), money=money+?,
                manager_trust=MIN(100,MAX(10,manager_trust+?))
            WHERE id=?
            """,
            (8 if position <= 3 else 3, prize, 5 if position <= 4 else -2, career_id),
        )
        db.commit()
        summary = (
            f"{career['season_label']} league campaign closed: {position} in {career['league_name']}. "
            f"${prize:,} was credited, {world_result['qualification_count']} continental entries were recorded, "
            f"and {offer_count} transfer-market opportunities were created."
        )
        if awards:
            summary += f" Awards: {', '.join(awards)}."
        return True, summary
    except Exception:
        db.rollback()
        raise


def start_next_season(career_id):
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    try:
        career = db.execute("SELECT * FROM careers WHERE id=?", (career_id,)).fetchone()
        if career is None:
            db.rollback()
            return False, "Career not found."
        if career["season_phase"] != "offseason":
            db.rollback()
            return False, "Close the current league season first."
        if career["calendar_week"] <= 52:
            db.rollback()
            return False, "Complete the remaining off-season calendar weeks first."
        next_number = career["season_number"] + 1
        next_label = _next_season_label(career["season_label"])
        initialize_world_memberships(db, career_id, next_number)
        membership = db.execute(
            """
            SELECT league_id FROM world_memberships
            WHERE career_id=? AND season_number=? AND club_id=?
            """,
            (career_id, next_number, career["club_id"]),
        ).fetchone()
        next_league_id = membership["league_id"] if membership else career["league_id"]
        db.execute(
            """
            UPDATE careers SET age=age+1, season_number=?, season_label=?, current_week=1,
                calendar_week=1, season_phase='offseason', league_id=?, weekly_action_used=0,
                fitness=MIN(100,fitness+12), morale=MIN(100,morale+4),
                stress=MAX(0,stress-10)
            WHERE id=?
            """,
            (next_number, next_label, next_league_id, career_id),
        )
        db.execute(
            """
            INSERT OR IGNORE INTO season_player_stats(career_id,season_number,season_label,club_id)
            VALUES (?,?,?,?)
            """,
            (career_id, next_number, next_label, career["club_id"]),
        )
        _create_season_world(career_id, next_number, next_league_id)
        generate_season_calendar(db, career_id, next_number, next_label, next_league_id)
        db.execute(
            "UPDATE player_contracts SET status='expired' WHERE career_id=? AND status='active' AND end_season<?",
            (career_id, next_number),
        )
        ensure_financial_profile(db, career_id)
        db.commit()
        league = get_league_row(db, next_league_id)
        return True, f"{next_label} begins with the July close-season programme at {league['name']}."
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



def _transfer_can_rebuild_current_schedule(db, career_id, season_number):
    """Only rebuild a current season before any fixture has become historical save data."""
    return db.execute(
        """
        SELECT 1 FROM fixtures
        WHERE career_id=? AND season_number=? AND played=1
        LIMIT 1
        """,
        (career_id, season_number),
    ).fetchone() is None


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
        if get_active_match_session(career_id) is not None:
            db.rollback()
            return False, "Finish the active match before completing a transfer."
        if career["season_phase"] != "offseason":
            db.rollback()
            return False, "Formal club changes are completed during the close-season window."
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
            (career_id, offer["season_number"], offer["to_club_id"], offer["to_league_id"]),
        ).fetchone()
        if membership is None:
            db.rollback()
            return False, "The destination club is not registered in that league for the target season."
        db.execute("UPDATE transfer_offers SET status='accepted' WHERE id=?", (offer_id,))
        db.execute(
            "UPDATE transfer_offers SET status='declined' WHERE career_id=? AND id<>? AND status='pending'",
            (career_id, offer_id),
        )
        db.execute(
            "UPDATE club_history SET left_season=? WHERE career_id=? AND left_season IS NULL",
            (career["season_number"], career_id),
        )
        db.execute(
            "INSERT INTO club_history(career_id,club_id,joined_season,reason) VALUES (?,?,?,'Transfer')",
            (career_id, offer["to_club_id"], offer["season_number"]),
        )
        squad_level = "first_team" if offer["squad_role"] in {"Important player", "First-team rotation"} else "reserve_bridge"
        trust = max(18, min(62, 54 - (club["strength"] - career["overall"])))
        db.execute("UPDATE player_contracts SET status='terminated' WHERE career_id=? AND status='active'", (career_id,))
        db.execute(
            """
            INSERT INTO player_contracts(
                career_id,club_id,start_season,end_season,weekly_wage,
                appearance_bonus,goal_bonus,assist_bonus,signing_bonus,squad_role,status
            ) VALUES (?,?,?,?,?,?,?,?,?,?,'active')
            """,
            (
                career_id, offer["to_club_id"], offer["season_number"],
                offer["season_number"] + offer["contract_years"], offer["wage"],
                max(75, offer["wage"] // 8), max(150, offer["wage"] // 4),
                max(100, offer["wage"] // 5), offer["signing_bonus"], offer["squad_role"],
            ),
        )
        db.execute(
            """
            UPDATE careers SET club_id=?, league_id=?, wage=?, money=money+?,
                morale=MIN(100,morale+8), squad_level=?, manager_trust=?,
                stress=MAX(0,stress-3)
            WHERE id=?
            """,
            (
                offer["to_club_id"], offer["to_league_id"], offer["wage"],
                offer["signing_bonus"], squad_level, trust, career_id,
            ),
        )
        if (
            offer["season_number"] == career["season_number"]
            and _transfer_can_rebuild_current_schedule(
                db, career_id, career["season_number"]
            )
        ):
            # A July transfer happens before the first competitive fixture. Rebuild
            # the active schedule around the destination league without mutating
            # wider world memberships or completed historical seasons.
            _create_season_world(career_id, career["season_number"], offer["to_league_id"])
            generate_season_calendar(
                db, career_id, career["season_number"], career["season_label"], offer["to_league_id"]
            )

        db.execute(
            """
            INSERT INTO finance_transactions(
                career_id,season_number,week,calendar_week,category,amount,description,
                reference_type,reference_id
            ) VALUES (?,?,?,?, 'Signing bonus', ?, ?, 'transfer', ?)
            """,
            (
                career_id, career["season_number"], career["current_week"], career["calendar_week"],
                offer["signing_bonus"],
                f"Signed for {club['name']} in {club['league_name']} — {offer['squad_role']}", offer_id,
            ),
        )
        db.commit()
        return True, (
            f"Transfer complete: {club['name']} ({club['league_name']}), "
            f"{offer['contract_years']}-year deal, {offer['squad_role'].lower()}, "
            f"${offer['wage']:,} per week."
        )
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


def get_calendar_dashboard(career_id):
    db = get_db()
    career = db.execute("SELECT * FROM careers WHERE id=?", (career_id,)).fetchone()
    if career is None:
        return {"weeks": [], "context": None}
    return {
        "weeks": get_calendar(db, career_id, career["season_number"]),
        "context": get_week_context(db, career),
    }


def get_calendar_context(career):
    if career is None:
        return None
    return get_week_context(get_db(), career)


def _apply_free_week_development(db, career, rng):
    focus = career["training_focus"] if career["training_focus"] in TRAINING_FOCUS else "balanced"
    if focus == "recovery":
        db.execute(
            "UPDATE careers SET xp=0, fitness=MIN(100,fitness+12), morale=MIN(100,morale+2), stress=MAX(0,stress-3) WHERE id=?",
            (career["id"],),
        )
        return "Recovery plan restored fitness and reduced stress."
    already_trained = _week_has_settled_match(db, career)
    gains = dict.fromkeys(ATTRIBUTES, 0) if already_trained else training_development_xp(
        focus=focus,
        position=career["position"],
        season_phase=career["season_phase"],
        minutes=0,
        unavailable_injured=career["injured_weeks"] > 0,
    )
    overall = career["overall"]
    upgrades = []
    # Zero-training weeks must not convert previously banked XP either.
    if any(gains.values()):
        row = db.execute("SELECT * FROM player_attributes WHERE career_id=?", (career["id"],)).fetchone()
        development = apply_attribute_xp(
            attributes={name: row[name] for name in ATTRIBUTES},
            meters={name: row[f"{name}_xp"] for name in ATTRIBUTES},
            gains=gains,
            position=career["position"],
            potential=career["potential"],
        )
        attrs = development["attributes"]
        meters = development["meters"]
        overall = development["overall"]
        upgrades = development["upgrades"]
        db.execute(
            """
            UPDATE player_attributes
            SET pace=?,shooting=?,passing=?,dribbling=?,defending=?,physical=?,
                pace_xp=?,shooting_xp=?,passing_xp=?,dribbling_xp=?,defending_xp=?,physical_xp=?
            WHERE career_id=?
            """,
            (*[attrs[name] for name in ATTRIBUTES], *[meters[name] for name in ATTRIBUTES], career["id"]),
        )
    db.execute(
        """
        UPDATE careers SET xp=0,overall=?,fitness=MIN(100,fitness+7),
            morale=MIN(100,morale+1),stress=MAX(0,stress-1),
            market_value=MAX(market_value,? * ? * 40)
        WHERE id=?
        """,
        (overall, overall, overall, career["id"]),
    )
    if already_trained:
        return "Match-week development already settled; fitness recovery completed."
    if career["injured_weeks"] > 0:
        return "Injury recovery restored fitness; no training XP awarded."
    if upgrades:
        return "Free-week breakthrough: " + ", ".join(
            f"{item['attribute'].title()} {item['from']} → {item['to']}" for item in upgrades
        ) + "."
    return f"{TRAINING_FOCUS[focus]['label']} added {sum(gains.values())} development XP."


def advance_calendar_week(career_id, seed=None):
    seed_value = int(seed) if seed is not None else secrets.randbits(63)
    rng = random.Random(seed_value)
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    try:
        career = get_active_career()
        if career is None or career["id"] != career_id:
            db.rollback()
            return False, "Career not found.", None
        if get_active_match_session(career_id) is not None:
            db.rollback()
            return False, "Finish or skip the active match first.", None
        if career["calendar_week"] > 52:
            db.rollback()
            return False, "The 52-week calendar is complete. Start the next season.", None
        context = get_week_context(db, career)
        if context["fixtures_this_week"]:
            fixture = context["fixtures_this_week"][0]
            db.rollback()
            return False, f"Play {fixture['home_name']} vs {fixture['away_name']} before advancing the week.", None
        if career["season_phase"] != "offseason" and season_is_complete(career) and career["calendar_week"] >= 48:
            db.rollback()
            return False, "The league campaign is complete. Close the season before entering the summer programme.", None

        finance = process_weekly_finances(db, career, career["calendar_week"], rng)
        international = process_international_week(db, career, career["calendar_week"], rng)
        fresh = get_active_career()
        development_message = _apply_free_week_development(db, fresh, rng)

        # Off-season weeks default to controlled recovery when the user does not
        # explicitly choose a programme. This prevents dead clicks while still
        # rewarding deliberate choices on the calendar or finance screen.
        action = economy_get_selected_player_programme(
            db,
            career_id,
            career["season_number"],
            career["calendar_week"],
        )
        if career["season_phase"] == "offseason" and action is None:
            db.execute(
                "UPDATE careers SET fitness=MIN(100,fitness+6),morale=MIN(100,morale+2),stress=MAX(0,stress-4) WHERE id=?",
                (career_id,),
            )

        db.execute(
            """
            UPDATE career_calendar_weeks SET status='completed'
            WHERE career_id=? AND season_number=? AND week=?
            """,
            (career_id, career["season_number"], career["calendar_week"]),
        )
        next_week = career["calendar_week"] + 1
        if career["season_phase"] == "offseason":
            next_phase = "offseason"
        elif next_week <= 5:
            next_phase = "preseason"
        else:
            next_phase = "competitive"
        db.execute(
            "UPDATE careers SET calendar_week=?,season_phase=?,weekly_action_used=0 WHERE id=?",
            (next_week, next_phase, career_id),
        )
        expire_market_offers(db, career_id, career["season_number"], next_week)
        db.commit()

        international_text = ""
        if international:
            status = international.get("status")
            if status == "selected":
                international_text = (
                    f" International duty: {international['appearances']} appearance(s), "
                    f"{international['goals']} goal(s), {international['assists']} assist(s)."
                )
            elif status == "not_selected":
                international_text = f" No {international['team']} call-up; the week became a recovery block."
            elif status == "not_qualified":
                international_text = f" {international['team']} did not qualify for {international['competition']}."
        return True, (
            f"Calendar week {career['calendar_week']} completed. Net cash flow: ${finance.get('net', 0):,}. "
            f"{development_message}{international_text}"
        ), {"finance": finance, "international": international, "next_week": next_week}
    except Exception:
        db.rollback()
        raise


def get_financial_dashboard(career_id):
    return economy_get_financial_dashboard(get_db(), career_id)


def accept_endorsement(career_id, endorsement_id):
    db = get_db()
    success, message = economy_accept_endorsement(db, career_id, endorsement_id)
    db.commit() if success else db.rollback()
    return success, message


def decline_endorsement(career_id, endorsement_id):
    db = get_db()
    success = economy_decline_endorsement(db, career_id, endorsement_id)
    db.commit()
    return success


def buy_investment(career_id, instrument_id, amount):
    db = get_db()
    success, message = economy_buy_investment(db, career_id, instrument_id, amount)
    db.commit() if success else db.rollback()
    return success, message


def sell_investment(career_id, instrument_id, percent):
    db = get_db()
    success, message = economy_sell_investment(db, career_id, instrument_id, percent)
    db.commit() if success else db.rollback()
    return success, message


def buy_property(career_id, property_id):
    db = get_db()
    success, message = economy_buy_property(db, career_id, property_id)
    db.commit() if success else db.rollback()
    return success, message


def place_virtual_wager(career_id, stake, risk, seed=None):
    db = get_db()
    rng = random.Random(int(seed) if seed is not None else secrets.randbits(63))
    success, message = economy_place_virtual_wager(db, career_id, stake, risk, rng)
    db.commit() if success else db.rollback()
    return success, message


def take_offseason_action(career_id, action):
    db = get_db()
    success, message = economy_take_offseason_action(db, career_id, action)
    db.commit() if success else db.rollback()
    return success, message


def get_international_summary(career_id):
    return international_get_summary(get_db(), career_id)


def get_market_dashboard(career_id):
    return transfer_get_market_dashboard(get_db(), career_id)


def request_agent_market_search(career_id, seed=None):
    db = get_db()
    career = get_active_career()
    if career is None or career["id"] != career_id:
        return False, "Career not found.", 0
    stats = get_season_stats(career_id, career["season_number"])
    rng = random.Random(int(seed) if seed is not None else secrets.randbits(63))
    success, message, count = transfer_request_agent_search(db, career, stats, rng)
    db.commit() if success else db.rollback()
    return success, message, count


def get_career_command_center(career_id):
    """Return one canonical snapshot of what the player should understand and do next.

    This is intentionally presentation-friendly but contains no Flask/UI logic. Every
    screen can render the same career state without rebuilding lifecycle rules in
    templates or JavaScript.
    """
    db = get_db()
    career = db.execute("SELECT * FROM careers WHERE id=?", (career_id,)).fetchone()
    if career is None:
        return None

    context = get_week_context(db, career)
    active_match = get_active_match_session(career_id)
    complete = season_is_complete(career)
    market = transfer_get_market_dashboard(db, career_id)
    finance = economy_get_financial_dashboard(db, career_id)

    pending_endorsements = db.execute(
        "SELECT COUNT(*) AS n FROM endorsements WHERE career_id=? AND status='pending'",
        (career_id,),
    ).fetchone()["n"]
    selected_programme = economy_get_selected_player_programme(
        db,
        career_id,
        career["season_number"],
        career["calendar_week"],
    )

    fixtures = list(context.get("fixtures_this_week") or []) if context else []
    events = list(context.get("events") or []) if context else []
    current_week = context.get("week") if context else None
    current_week_data = dict(current_week) if current_week else None
    event_data = [dict(item) for item in events[:4]]

    if active_match is not None:
        primary = {
            "kind": "resume_match",
            "label": "Resume active match",
            "detail": "A sealed match is already in progress. Finish or skip it before anything else advances.",
            "session_id": active_match["public_id"],
            "tone": "urgent",
        }
    elif context and context.get("can_play") and fixtures:
        fixture = fixtures[0]
        primary = {
            "kind": "play_match",
            "label": f"Play {fixture['home_name']} vs {fixture['away_name']}",
            "detail": "This club fixture is the blocking event for the current week. The calendar cannot advance until it is resolved.",
            "tone": "match",
        }
    elif complete and career["season_phase"] != "offseason":
        primary = {
            "kind": "close_season",
            "label": "Close competitive season",
            "detail": "The league programme is complete. Finalise standings, awards and the summer transition.",
            "tone": "season",
        }
    elif context and context.get("calendar_complete") and career["season_phase"] == "offseason":
        primary = {
            "kind": "start_season",
            "label": "Begin next pre-season",
            "detail": "The 52-week cycle is complete and the next football season is ready to be created.",
            "tone": "season",
        }
    else:
        primary = {
            "kind": "advance_week",
            "label": "Advance one week",
            "detail": "No blocking club fixture remains. Finances, development and any international duty will resolve together.",
            "tone": "calendar",
        }

    decisions = []
    if active_match is not None:
        decisions.append({"kind": "match", "label": "Finish active match", "detail": "All other weekly progression is locked.", "priority": 100})
    elif fixtures:
        decisions.append({"kind": "match", "label": "Club match waiting", "detail": f"{fixtures[0]['home_name']} vs {fixtures[0]['away_name']}", "priority": 90})
    if market.get("offers"):
        decisions.append({"kind": "market", "label": f"{len(market['offers'])} transfer offer(s)", "detail": "Formal contracts are waiting for a decision.", "priority": 70})
    elif market.get("watching"):
        decisions.append({"kind": "market", "label": f"{len(market['watching'])} club(s) watching", "detail": "Recruitment interest is developing.", "priority": 35})
    if pending_endorsements:
        decisions.append({"kind": "finance", "label": f"{pending_endorsements} sponsorship offer(s)", "detail": "Commercial terms are waiting in Finances.", "priority": 60})
    if (
        context
        and not context.get("calendar_complete")
        and any(item["event_type"] == "offseason" for item in events)
        and selected_programme is None
        and not fixtures
    ):
        decisions.append({"kind": "calendar", "label": "Choose a player programme", "detail": "Use this free week deliberately before advancing it.", "priority": 50})
    if career["fitness"] < 60:
        decisions.append({"kind": "development", "label": "Fitness needs attention", "detail": f"Current fitness is {career['fitness']}%. A recovery focus may be safer.", "priority": 45})
    decisions.sort(key=lambda item: item["priority"], reverse=True)

    last_transaction = db.execute(
        """
        SELECT category, amount, description, calendar_week
        FROM finance_transactions WHERE career_id=? ORDER BY id DESC LIMIT 1
        """,
        (career_id,),
    ).fetchone()
    recent_reports = get_recent_reports(career_id, 1)
    last_match = recent_reports[0] if recent_reports else None

    return {
        "week": int(career["calendar_week"]),
        "week_total": 52,
        "progress_pct": round(max(0, min(52, int(career["calendar_week"]))) / 52 * 100, 1),
        "phase": career["season_phase"],
        "season_label": career["season_label"],
        "current_week": current_week_data,
        "events": event_data,
        "primary": primary,
        "decisions": decisions[:5],
        "selected_programme": selected_programme["title"] if selected_programme else None,
        "market_offer_count": len(market.get("offers") or []),
        "watching_count": len(market.get("watching") or []),
        "pending_endorsements": int(pending_endorsements or 0),
        "cash": int(career["money"]),
        "net_worth": int(finance.get("net_worth") or career["money"]),
        "fitness": int(career["fitness"]),
        "morale": int(career["morale"]),
        "stress": int(career["stress"]),
        "last_transaction": dict(last_transaction) if last_transaction else None,
        "last_match": dict(last_match) if last_match else None,
    }
