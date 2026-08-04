from __future__ import annotations

import random
from typing import Any


def _performance_level(career, season_stats) -> float:
    appearances = int(season_stats["appearances"] or 0)
    average = float(season_stats["average_rating"] or 0)
    contributions = int(season_stats["goals"] or 0) + int(season_stats["assists"] or 0)
    return (
        career["overall"]
        + career["reputation"] * 0.16
        + max(0.0, average - 6.0) * 4.2
        + min(10.0, contributions * 0.32)
        + min(4.0, appearances / 8)
    )


def _role_for_move(player_level: float, club_strength: int) -> str:
    difference = player_level - club_strength
    if difference >= 5:
        return "Important player"
    if difference >= -2:
        return "First-team rotation"
    if difference >= -7:
        return "Development prospect"
    return "Reserve pathway"


def _offer_type(current, destination) -> str:
    strength_jump = destination["strength"] - current["strength"]
    league_jump = destination["league_reputation"] - current["league_reputation"]
    if strength_jump >= 9 or league_jump >= 12:
        return "ambitious_step"
    if strength_jump >= 2 or league_jump >= 4:
        return "step_up"
    if strength_jump <= -6 and destination["youth_rating"] >= 70:
        return "development_project"
    return "first_team_opportunity"


def generate_transfer_market(
    db,
    career,
    season_stats,
    rng: random.Random,
    target_season: int,
    *,
    extra_search: bool = False,
) -> int:
    """Generate a broad but believable market instead of two arbitrary offers."""
    current = db.execute(
        """
        SELECT c.*, l.reputation AS league_reputation, l.name AS league_name
        FROM clubs c JOIN leagues l ON l.id=? WHERE c.id=?
        """,
        (career["league_id"], career["club_id"]),
    ).fetchone()
    if current is None:
        return 0
    player_level = _performance_level(career, season_stats)
    rows = db.execute(
        """
        SELECT c.*, wm.league_id AS destination_league_id,
               l.name AS league_name, l.reputation AS league_reputation,
               l.tier AS league_tier, co.name AS country_name
        FROM world_memberships wm
        JOIN clubs c ON c.id=wm.club_id
        JOIN leagues l ON l.id=wm.league_id
        JOIN countries co ON co.id=l.country_id
        WHERE wm.career_id=? AND wm.season_number=? AND c.id<>?
        """,
        (career["id"], target_season, career["club_id"]),
    ).fetchall()
    scored: list[tuple[float, Any]] = []
    for club in rows:
        ability_gap = club["strength"] - player_level
        # Great clubs can watch a prospect, but absurd jumps remain extremely unlikely.
        if ability_gap > 17 + career["agent_quality"] / 10:
            continue
        if club["league_reputation"] > current["league_reputation"] + 24 and career["reputation"] < 55:
            continue
        fit = max(0.0, 28 - abs(ability_gap) * 2.0)
        upward = max(-4.0, (club["strength"] - current["strength"]) * 0.62)
        league_value = (club["league_reputation"] - current["league_reputation"]) * 0.28
        youth_fit = club["youth_rating"] * (0.05 if career["age"] <= 21 else 0.015)
        playing_time = max(-8.0, 9 - max(0, ability_gap) * 1.2)
        noise = rng.uniform(-5.0, 5.0)
        interest = fit + upward + league_value + youth_fit + playing_time + noise
        if extra_search:
            interest += career["agent_quality"] * 0.08
        if interest >= 10:
            scored.append((interest, club))

    scored.sort(key=lambda item: item[0], reverse=True)
    base_count = 4
    if int(season_stats["appearances"] or 0) >= 12:
        base_count += 2
    if float(season_stats["average_rating"] or 0) >= 7.0:
        base_count += 2
    if career["reputation"] >= 40:
        base_count += 2
    if extra_search:
        base_count += 3
    target_count = max(4, min(12, base_count))

    selected: list[tuple[float, Any]] = []
    league_counts: dict[int, int] = {}
    country_counts: dict[str, int] = {}
    for interest, club in scored:
        league_count = league_counts.get(club["destination_league_id"], 0)
        country_count = country_counts.get(club["country_name"], 0)
        if league_count >= 2 or country_count >= 4:
            continue
        if db.execute(
            """
            SELECT 1 FROM transfer_offers
            WHERE career_id=? AND season_number=? AND to_club_id=? AND status IN ('pending','watching')
            """,
            (career["id"], target_season, club["id"]),
        ).fetchone():
            continue
        selected.append((interest, club))
        league_counts[club["destination_league_id"]] = league_count + 1
        country_counts[club["country_name"]] = country_count + 1
        if len(selected) >= target_count:
            break

    for interest, club in selected:
        role = _role_for_move(player_level, club["strength"])
        offer_type = _offer_type(current, club)
        wage_base = (
            club["strength"] * 14
            + club["league_reputation"] * 9
            + career["overall"] * 7
            + career["reputation"] * 4
        )
        role_multiplier = {
            "Important player": 1.18,
            "First-team rotation": 1.00,
            "Development prospect": 0.82,
            "Reserve pathway": 0.68,
        }[role]
        wage = max(career["wage"] + 50, round(wage_base * role_multiplier / 50) * 50)
        contract_years = rng.randint(2, 5)
        signing_bonus = wage * rng.randint(5, 14)
        status = "pending" if interest >= 18 else "watching"
        recommendation = (
            "Strong sporting and financial fit"
            if interest >= 28
            else "Realistic option with trade-offs"
            if interest >= 20
            else "Club is monitoring before a formal approach"
        )
        db.execute(
            """
            INSERT INTO transfer_offers(
                career_id, season_number, from_club_id, to_club_id,
                wage, signing_bonus, to_league_id, status,
                offer_type, squad_role, contract_years, interest_score,
                agent_recommendation, expires_calendar_week
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                career["id"], target_season, career["club_id"], club["id"],
                wage, signing_bonus, club["destination_league_id"], status,
                offer_type, role, contract_years, round(interest, 1), recommendation, 8,
            ),
        )
    return len(selected)


def request_agent_search(db, career, season_stats, rng: random.Random) -> tuple[bool, str, int]:
    if career["season_phase"] != "offseason":
        return False, "Active transfer searches are available during the close-season window.", 0
    existing = db.execute(
        """
        SELECT 1 FROM career_week_actions
        WHERE career_id=? AND season_number=? AND calendar_week=? AND action_type='agent_search'
        """,
        (career["id"], career["season_number"], career["calendar_week"]),
    ).fetchone()
    if existing:
        return False, "Your agent has already contacted clubs this week.", 0
    fee = max(250, career["wage"] // 2)
    if career["money"] < fee:
        return False, "Not enough available cash for the agent search fee.", 0
    target_season = (
        career["season_number"] + 1
        if career["season_phase"] == "offseason" and career["calendar_week"] >= 49
        else career["season_number"]
    )
    count = generate_transfer_market(db, career, season_stats, rng, target_season, extra_search=True)
    db.execute(
        """
        INSERT INTO career_week_actions(career_id,season_number,calendar_week,action_type,title,effects_json)
        VALUES (?,?,?,?,?,?)
        """,
        (
            career["id"], career["season_number"], career["calendar_week"], "agent_search",
            "Agent market search", '{"market_visibility":true}',
        ),
    )
    db.execute("UPDATE careers SET money=money-?, stress=MIN(100,stress+3) WHERE id=?", (fee, career["id"]))
    db.execute(
        """
        INSERT INTO finance_transactions(
            career_id,season_number,week,calendar_week,category,amount,description
        ) VALUES (?,?,?,?, 'Agent services', ?, ?)
        """,
        (
            career["id"], career["season_number"], career["current_week"], career["calendar_week"],
            -fee, f"Active transfer-market search; {count} new approaches or monitoring records",
        ),
    )
    return True, f"Your agent contacted the market and generated {count} new opportunity records.", count


def expire_market_offers(db, career_id: int, season_number: int, calendar_week: int) -> int:
    cursor = db.execute(
        """
        UPDATE transfer_offers SET status='expired'
        WHERE career_id=? AND season_number=? AND status IN ('pending','watching')
          AND expires_calendar_week IS NOT NULL AND expires_calendar_week<?
        """,
        (career_id, season_number, calendar_week),
    )
    return cursor.rowcount


def get_market_dashboard(db, career_id: int) -> dict[str, Any]:
    career = db.execute("SELECT * FROM careers WHERE id=?", (career_id,)).fetchone()
    if career is None:
        return {"offers": [], "watching": [], "history": []}
    target_seasons = (career["season_number"], career["season_number"] + 1)
    rows = db.execute(
        """
        SELECT transfer_offers.*, source.name AS from_name, destination.name AS to_name,
               destination.strength AS to_strength, destination.reputation AS to_reputation,
               destination.youth_rating AS to_youth_rating,
               l.name AS to_league_name, l.reputation AS to_league_reputation,
               l.tier AS to_league_tier, co.name AS to_country_name
        FROM transfer_offers
        JOIN clubs source ON source.id=transfer_offers.from_club_id
        JOIN clubs destination ON destination.id=transfer_offers.to_club_id
        LEFT JOIN leagues l ON l.id=transfer_offers.to_league_id
        LEFT JOIN countries co ON co.id=l.country_id
        WHERE transfer_offers.career_id=? AND transfer_offers.season_number IN (?,?)
        ORDER BY
          CASE transfer_offers.status WHEN 'pending' THEN 0 WHEN 'watching' THEN 1 ELSE 2 END,
          transfer_offers.interest_score DESC, l.reputation DESC
        """,
        (career_id, *target_seasons),
    ).fetchall()
    return {
        "career": career,
        "offers": [row for row in rows if row["status"] == "pending"],
        "watching": [row for row in rows if row["status"] == "watching"],
        "history": [row for row in rows if row["status"] not in {"pending", "watching"}],
        "window_open": career["season_phase"] == "offseason",
    }
