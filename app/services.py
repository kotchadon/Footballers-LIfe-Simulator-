from __future__ import annotations

import random

from .db import get_db
from .engine import (
    POSITION_WEIGHTS,
    build_commentary_events,
    commentary_to_text,
    calculate_overall,
    create_starting_attributes,
    player_selection_probability,
    simulate_player_performance,
    simulate_score,
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
        for index in range(len(teams) // 2):
            first, second = teams[index], teams[-1 - index]
            if first is not None and second is not None:
                fixtures.append((first, second) if round_index % 2 == 0 else (second, first))
        rounds.append(fixtures)
        teams = [teams[0], teams[-1], *teams[1:-1]]
    second_half = [[(away, home) for home, away in fixtures] for fixtures in rounds]
    return rounds + second_half


def _create_season_world(career_id, season_number):
    db = get_db()
    clubs = db.execute("SELECT id FROM clubs ORDER BY id").fetchall()
    club_ids = [row["id"] for row in clubs]

    db.execute("DELETE FROM standings WHERE career_id = ?", (career_id,))
    for club_id in club_ids:
        db.execute("INSERT INTO standings(career_id, club_id) VALUES (?, ?)", (career_id, club_id))

    for week, fixtures in enumerate(round_robin(club_ids), start=1):
        for home_id, away_id in fixtures:
            db.execute(
                """
                INSERT INTO fixtures(career_id, season_number, week, home_club_id, away_club_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (career_id, season_number, week, home_id, away_id),
            )


def create_career(player_name, nationality, position):
    seed_clubs()
    db = get_db()
    rng = random.Random()
    starting_club = db.execute("SELECT * FROM clubs ORDER BY strength ASC LIMIT 1").fetchone()
    attributes = create_starting_attributes(position, rng)
    overall = calculate_overall(attributes, position, potential=88)

    cursor = db.execute(
        """
        INSERT INTO careers(player_name, nationality, position, overall, club_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (player_name.strip(), nationality.strip(), position, overall, starting_club["id"]),
    )
    career_id = cursor.lastrowid

    db.execute("INSERT INTO player_stats(career_id) VALUES (?)", (career_id,))
    db.execute(
        """
        INSERT INTO player_attributes(
            career_id, pace, shooting, passing, dribbling, defending, physical
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            career_id,
            attributes["pace"],
            attributes["shooting"],
            attributes["passing"],
            attributes["dribbling"],
            attributes["defending"],
            attributes["physical"],
        ),
    )
    db.execute(
        """
        INSERT INTO season_player_stats(career_id, season_number, season_label, club_id)
        VALUES (?, 1, '2026/27', ?)
        """,
        (career_id, starting_club["id"]),
    )
    db.execute(
        """
        INSERT INTO club_history(career_id, club_id, joined_season, reason)
        VALUES (?, ?, 1, 'Academy graduate')
        """,
        (career_id, starting_club["id"]),
    )
    _create_season_world(career_id, 1)
    db.commit()
    return career_id


def get_active_career():
    return get_db().execute(
        """
        SELECT careers.*, clubs.name AS club_name, clubs.short_name,
               clubs.strength AS club_strength, clubs.reputation AS club_reputation,
               pa.pace, pa.shooting, pa.passing, pa.dribbling, pa.defending, pa.physical
        FROM careers
        JOIN clubs ON clubs.id = careers.club_id
        JOIN player_attributes pa ON pa.career_id = careers.id
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
        WHERE fixtures.career_id = ? AND fixtures.season_number = ? AND fixtures.week = ?
          AND fixtures.played = 0
          AND (fixtures.home_club_id = ? OR fixtures.away_club_id = ?)
        LIMIT 1
        """,
        (
            career["id"],
            career["season_number"],
            career["current_week"],
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


def play_next_week(career_id, seed=None):
    rng = random.Random(seed)
    db = get_db()
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

    week = career["current_week"]
    fixtures = db.execute(
        """
        SELECT f.*, h.strength AS home_strength, a.strength AS away_strength,
               h.name AS home_name, a.name AS away_name
        FROM fixtures f
        JOIN clubs h ON h.id = f.home_club_id
        JOIN clubs a ON a.id = f.away_club_id
        WHERE f.career_id = ? AND f.season_number = ? AND f.week = ? AND f.played = 0
        ORDER BY f.id
        """,
        (career_id, career["season_number"], week),
    ).fetchall()
    if not fixtures:
        return None

    training_focus = career["training_focus"] if career["training_focus"] in TRAINING_FOCUS else "balanced"
    training_plan = TRAINING_FOCUS[training_focus]
    recovery_gain = rng.randint(13, 17) if training_focus == "recovery" else rng.randint(8, 12)
    pre_match_fitness = min(100, career["fitness"] + recovery_gain)
    player_report = None

    for fixture in fixtures:
        result = simulate_score(fixture["home_strength"], fixture["away_strength"], rng)
        db.execute(
            "UPDATE fixtures SET played = 1, home_goals = ?, away_goals = ? WHERE id = ?",
            (result.home_goals, result.away_goals, fixture["id"]),
        )
        update_standing(career_id, fixture["home_club_id"], result.home_goals, result.away_goals)
        update_standing(career_id, fixture["away_club_id"], result.away_goals, result.home_goals)

        if career["club_id"] not in (fixture["home_club_id"], fixture["away_club_id"]):
            continue

        selection_status, minutes = _selection_status(career, rng, fitness=pre_match_fitness)
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
                "injured": f"You miss the match through injury. {career['injured_weeks']} week(s) remained before this match.",
                "suspended": "You watch from the stands while serving a suspension.",
                "bench": "You are named on the bench but the manager does not bring you on.",
            }[selection_status]
            events = build_commentary_events(
                career["player_name"],
                0,
                0,
                0.0,
                team_goals,
                opponent_goals,
                selection_status,
                0,
                0,
                0,
                False,
                rng,
            )
            events.insert(1, {"minute": 1, "text": reason, "kind": "player"})
            events[-1]["text"] = "Full time. You did not enter the pitch."
            performance = {
                "goals": 0,
                "assists": 0,
                "yellow_cards": 0,
                "red_cards": 0,
                "injured": False,
                "injury_weeks": 0,
                "rating": 0.0,
                "motm": False,
                "events": events,
                "commentary": commentary_to_text(events),
            }

        win = int(team_goals > opponent_goals)
        draw = int(team_goals == opponent_goals)
        loss = int(team_goals < opponent_goals)

        if appeared:
            _update_stats_table(db, "player_stats", career, selection_status, minutes, performance, win, draw, loss)
            _update_stats_table(
                db, "season_player_stats", career, selection_status, minutes, performance, win, draw, loss
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

        match_xp = 0
        if appeared:
            match_xp = max(2, round(performance["rating"] * 1.5)) + performance["goals"] * 5 + performance["assists"] * 3
        training_xp = 0
        if career["injured_weeks"] == 0 and training_focus != "recovery":
            training_xp = training_plan["weekly_xp"]
            if appeared and performance["rating"] >= 7.5:
                training_xp += 2

        existing_injury = career["injured_weeks"]
        existing_suspension = career["suspended_matches"]
        injury_weeks = max(0, existing_injury - 1) if selection_status == "injured" else existing_injury
        suspension_matches = max(0, existing_suspension - 1) if selection_status == "suspended" else existing_suspension
        if performance["injured"]:
            injury_weeks = max(injury_weeks, performance["injury_weeks"])
            db.execute("UPDATE player_stats SET injuries = injuries + 1 WHERE career_id = ?", (career_id,))
        if performance["red_cards"]:
            suspension_matches = max(suspension_matches, rng.randint(1, 3))

        yellow_accumulation = career["yellow_card_accumulation"] + performance["yellow_cards"]
        if yellow_accumulation >= 5:
            suspension_matches = max(suspension_matches, 1)
            yellow_accumulation -= 5

        refreshed = db.execute(
            """
            SELECT careers.*, pa.pace, pa.shooting, pa.passing, pa.dribbling, pa.defending, pa.physical
            FROM careers JOIN player_attributes pa ON pa.career_id = careers.id
            WHERE careers.id = ?
            """,
            (career_id,),
        ).fetchone()
        development = _apply_xp(
            db,
            refreshed,
            match_xp + training_xp,
            rng,
            preferred_focus=training_focus,
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

        weekly_income = career["wage"]
        bonus = performance["goals"] * 75 + performance["assists"] * 40 + int(performance["motm"]) * 100
        db.execute(
            """
            UPDATE careers
            SET fitness = ?,
                morale = MIN(100, MAX(15, morale + ?)),
                reputation = MIN(100, reputation + ?),
                money = money + ?,
                injured_weeks = ?, suspended_matches = ?, yellow_card_accumulation = ?
            WHERE id = ?
            """,
            (
                fitness_after,
                morale_change,
                reputation_gain,
                weekly_income + bonus,
                injury_weeks,
                suspension_matches,
                yellow_accumulation,
                career_id,
            ),
        )

        db.execute(
            """
            INSERT INTO match_reports(
                career_id, season_number, week, fixture_id, player_started, selection_status,
                player_minutes, player_goals, player_assists, player_yellow_cards,
                player_red_cards, player_injured, player_rating, player_motm, commentary,
                development_summary, fitness_before, fitness_after
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                career_id,
                career["season_number"],
                week,
                fixture["id"],
                int(selection_status == "starter"),
                selection_status,
                minutes,
                performance["goals"],
                performance["assists"],
                performance["yellow_cards"],
                performance["red_cards"],
                int(performance["injured"]),
                performance["rating"],
                int(performance["motm"]),
                performance["commentary"],
                development_summary,
                pre_match_fitness,
                fitness_after,
            ),
        )

        db.execute(
            """
            INSERT INTO finance_transactions(career_id, season_number, week, category, amount, description)
            VALUES (?, ?, ?, 'Wages', ?, ?)
            """,
            (career_id, career["season_number"], week, weekly_income, f"Weekly wage from {fixture['home_name'] if player_team_is_home else fixture['away_name']}"),
        )
        if bonus:
            db.execute(
                """
                INSERT INTO finance_transactions(career_id, season_number, week, category, amount, description)
                VALUES (?, ?, ?, 'Match bonus', ?, 'Goals, assists and performance bonus')
                """,
                (career_id, career["season_number"], week, bonus),
            )

        player_report = {
            "fixture_id": fixture["id"],
            "home_name": fixture["home_name"],
            "away_name": fixture["away_name"],
            "home_goals": result.home_goals,
            "away_goals": result.away_goals,
            "selection_status": selection_status,
            "minutes": minutes,
            "started": selection_status == "starter",
            "player_team_is_home": player_team_is_home,
            "development_summary": development_summary,
            "fitness_before": pre_match_fitness,
            "fitness_after": fitness_after,
            **performance,
        }

    max_week = db.execute(
        "SELECT MAX(week) AS max_week FROM fixtures WHERE career_id = ? AND season_number = ?",
        (career_id, career["season_number"]),
    ).fetchone()["max_week"]
    next_week = min(week + 1, max_week + 1)
    db.execute(
        "UPDATE careers SET current_week = ?, weekly_action_used = 0 WHERE id = ?",
        (next_week, career_id),
    )
    db.commit()
    return player_report


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
        "SELECT MAX(week) AS max_week FROM fixtures WHERE career_id = ? AND season_number = ?",
        (career["id"], career["season_number"]),
    ).fetchone()
    return max_week_row["max_week"] is not None and career["current_week"] > max_week_row["max_week"]


def _next_season_label(label):
    start = int(label.split("/")[0]) + 1
    return f"{start}/{str(start + 1)[-2:]}"


def _generate_transfer_offers(db, career, season_stats, rng):
    if season_stats["appearances"] < 4:
        return

    current_club = db.execute("SELECT * FROM clubs WHERE id = ?", (career["club_id"],)).fetchone()
    performance_score = (
        career["overall"]
        + career["reputation"] / 6
        + season_stats["average_rating"]
        + min(8, (season_stats["goals"] + season_stats["assists"]) / 3)
    )
    clubs = db.execute(
        "SELECT * FROM clubs WHERE id != ? ORDER BY strength ASC", (career["club_id"],)
    ).fetchall()
    candidates = [
        club
        for club in clubs
        if club["strength"] > current_club["strength"] and club["strength"] <= performance_score + 7
    ]
    if not candidates:
        candidates = [club for club in clubs if club["strength"] > current_club["strength"]][:1]

    rng.shuffle(candidates)
    for club in sorted(candidates[:3], key=lambda item: item["strength"]):
        wage = max(career["wage"] + 100, round((club["strength"] * 12 + career["overall"] * 5) / 50) * 50)
        signing_bonus = wage * rng.randint(3, 7)
        db.execute(
            """
            INSERT INTO transfer_offers(
                career_id, season_number, from_club_id, to_club_id, wage, signing_bonus
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                career["id"],
                career["season_number"] + 1,
                career["club_id"],
                club["id"],
                wage,
                signing_bonus,
            ),
        )


def finalize_season(career_id, seed=None):
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
        return False, "Career not found."
    if not season_is_complete(career):
        return False, "The season is not complete yet."
    if db.execute(
        "SELECT 1 FROM season_history WHERE career_id = ? AND season_number = ?",
        (career_id, career["season_number"]),
    ).fetchone():
        return False, "This season has already been finalised."

    standings = get_standings(career_id)
    position = next(index for index, row in enumerate(standings, start=1) if row["club_id"] == career["club_id"])
    club_row = next(row for row in standings if row["club_id"] == career["club_id"])
    season_stats = get_season_stats(career_id, career["season_number"])
    average_rating = season_stats["average_rating"]

    awards = []
    if position == 1:
        awards.append("League Champion")
    if season_stats["appearances"] >= 7 and average_rating >= 7.2:
        awards.append("Club Player of the Season")
    if season_stats["appearances"] >= 8 and average_rating >= 7.8:
        awards.append("Football Player of the Season")
    if season_stats["goals"] >= 12:
        awards.append("Club Top Scorer")
    if season_stats["assists"] >= 10:
        awards.append("Club Assist Leader")

    db.execute(
        """
        INSERT INTO season_history(
            career_id, season_number, season_label, club_id, league_position, league_points,
            appearances, goals, assists, average_rating, awards
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            career_id,
            career["season_number"],
            career["season_label"],
            career["club_id"],
            position,
            club_row["points"],
            season_stats["appearances"],
            season_stats["goals"],
            season_stats["assists"],
            average_rating,
            ", ".join(awards),
        ),
    )

    prize = max(500, (len(standings) - position + 1) * 350)
    if position == 1:
        prize += 2500
    if awards:
        prize += len(awards) * 400
    db.execute(
        """
        INSERT INTO finance_transactions(career_id, season_number, week, category, amount, description)
        VALUES (?, ?, ?, 'Season rewards', ?, ?)
        """,
        (career_id, career["season_number"], career["current_week"], prize, f"League finish: {position}; awards: {', '.join(awards) or 'none'}"),
    )

    _generate_transfer_offers(db, career, season_stats, rng)

    next_number = career["season_number"] + 1
    next_label = _next_season_label(career["season_label"])
    db.execute(
        """
        UPDATE careers
        SET age = age + 1, season_number = ?, season_label = ?, current_week = 1,
            weekly_action_used = 0, fitness = MIN(100, fitness + 20),
            morale = MIN(100, morale + ?), money = money + ?
        WHERE id = ?
        """,
        (next_number, next_label, 8 if position <= 3 else 3, prize, career_id),
    )
    db.execute(
        """
        INSERT INTO season_player_stats(career_id, season_number, season_label, club_id)
        VALUES (?, ?, ?, ?)
        """,
        (career_id, next_number, next_label, career["club_id"]),
    )
    _create_season_world(career_id, next_number)
    db.commit()
    summary = f"{career['season_label']} complete: finished {position}, earned ${prize:,}."
    if awards:
        summary += f" Awards: {', '.join(awards)}."
    return True, summary


def get_pending_transfer_offers(career_id):
    return get_db().execute(
        """
        SELECT transfer_offers.*, source.name AS from_name, destination.name AS to_name,
               destination.strength AS to_strength, destination.reputation AS to_reputation
        FROM transfer_offers
        JOIN clubs source ON source.id = transfer_offers.from_club_id
        JOIN clubs destination ON destination.id = transfer_offers.to_club_id
        WHERE transfer_offers.career_id = ? AND transfer_offers.status = 'pending'
        ORDER BY destination.strength DESC
        """,
        (career_id,),
    ).fetchall()


def accept_transfer_offer(career_id, offer_id):
    db = get_db()
    offer = db.execute(
        "SELECT * FROM transfer_offers WHERE id = ? AND career_id = ? AND status = 'pending'",
        (offer_id, career_id),
    ).fetchone()
    if offer is None:
        return False, "Transfer offer is no longer available."

    career = db.execute("SELECT * FROM careers WHERE id = ?", (career_id,)).fetchone()
    club = db.execute("SELECT * FROM clubs WHERE id = ?", (offer["to_club_id"],)).fetchone()
    db.execute(
        "UPDATE transfer_offers SET status = 'accepted' WHERE id = ?", (offer_id,)
    )
    db.execute(
        "UPDATE transfer_offers SET status = 'declined' WHERE career_id = ? AND status = 'pending'",
        (career_id,),
    )
    db.execute(
        "UPDATE club_history SET left_season = ? WHERE career_id = ? AND left_season IS NULL",
        (career["season_number"], career_id),
    )
    db.execute(
        """
        INSERT INTO club_history(career_id, club_id, joined_season, reason)
        VALUES (?, ?, ?, 'Transfer')
        """,
        (career_id, offer["to_club_id"], career["season_number"]),
    )
    db.execute(
        """
        UPDATE careers
        SET club_id = ?, wage = ?, money = money + ?, morale = MIN(100, morale + 8)
        WHERE id = ?
        """,
        (offer["to_club_id"], offer["wage"], offer["signing_bonus"], career_id),
    )
    db.execute(
        "UPDATE season_player_stats SET club_id = ? WHERE career_id = ? AND season_number = ?",
        (offer["to_club_id"], career_id, career["season_number"]),
    )
    db.execute(
        """
        INSERT INTO finance_transactions(career_id, season_number, week, category, amount, description)
        VALUES (?, ?, ?, 'Signing bonus', ?, ?)
        """,
        (career_id, career["season_number"], career["current_week"], offer["signing_bonus"], f"Signed for {club['name']}"),
    )
    db.commit()
    return True, f"Transfer complete: you joined {club['name']} on ${offer['wage']:,} per week."


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
        SELECT season_history.*, clubs.name AS club_name
        FROM season_history JOIN clubs ON clubs.id = season_history.club_id
        WHERE season_history.career_id = ? ORDER BY season_number DESC
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

