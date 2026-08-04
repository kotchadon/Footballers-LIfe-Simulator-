from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any


INTERNATIONAL_WINDOWS = {
    14: ("international", "September–October international window"),
    15: ("international", "September–October international window"),
    21: ("international", "November international window"),
    36: ("international", "March international window"),
    48: ("international", "June international window"),
}

TRANSFER_WEEKS = set(range(1, 10)) | set(range(30, 35))


def season_start_year(label: str) -> int:
    try:
        return int(str(label).split("/")[0])
    except (TypeError, ValueError):
        return 2026


def season_end_year(label: str) -> int:
    return season_start_year(label) + 1


def first_monday_of_july(year: int) -> date:
    current = date(year, 7, 1)
    return current + timedelta(days=(7 - current.weekday()) % 7)


def tournament_for_season(label: str, confederation: str | None = None) -> str | None:
    """Return the main summer national-team finals for this season.

    The career season is July–June. A 2029/30 season therefore ends in the
    2030 World Cup year.
    """
    end_year = season_end_year(label)
    confederation = (confederation or "").upper()
    if end_year >= 2026 and (end_year - 2026) % 4 == 0:
        return "FIFA World Cup"
    if confederation == "UEFA" and end_year >= 2028 and (end_year - 2028) % 4 == 0:
        return "UEFA European Championship"
    if confederation == "CONMEBOL" and end_year >= 2028 and (end_year - 2028) % 4 == 0:
        return "Copa América"
    if confederation == "AFC" and end_year >= 2027 and (end_year - 2027) % 4 == 0:
        return "AFC Asian Cup"
    if confederation == "CONCACAF" and end_year >= 2027 and (end_year - 2027) % 2 == 0:
        return "CONCACAF Gold Cup"
    return None


def nations_league_active(label: str, confederation: str | None) -> bool:
    return (confederation or "").upper() == "UEFA" and season_start_year(label) % 2 == 0


def _phase_for_week(week: int) -> str:
    if week <= 3:
        return "offseason"
    if week <= 5:
        return "preseason"
    if week <= 47:
        return "competitive"
    if week <= 50:
        return "international_finals"
    return "offseason"


def _spread(values: list[int], count: int) -> list[int]:
    if count <= 0:
        return []
    if count >= len(values):
        return values[:count]
    if count == 1:
        return [values[len(values) // 2]]
    positions = []
    for index in range(count):
        raw = round(index * (len(values) - 1) / (count - 1))
        positions.append(values[raw])
    # Rounding can theoretically duplicate an index on very short ranges.
    result: list[int] = []
    used: set[int] = set()
    for value in positions:
        if value not in used:
            result.append(value)
            used.add(value)
    for value in values:
        if len(result) == count:
            break
        if value not in used:
            result.append(value)
            used.add(value)
    return sorted(result)


def _league_calendar_weeks(round_count: int) -> list[int]:
    """Map league rounds to a July–May club season.

    Long second-division schedules use deliberate double-match weeks rather
    than stealing the close season or international windows. Duplicate week
    numbers are therefore valid and represent a midweek plus weekend round.
    """
    candidates = [week for week in range(6, 48) if week not in {14, 15, 21, 36}]
    if round_count <= len(candidates):
        return _spread(candidates, round_count)
    result = list(candidates)
    extra_count = round_count - len(candidates)
    double_week_pool = [week for week in candidates if week not in {12, 19, 28, 35, 42, 47}]
    result.extend(_spread(double_week_pool, extra_count))
    return sorted(result)


def _add_event(
    db,
    career_id: int,
    season_number: int,
    week: int,
    event_type: str,
    title: str,
    description: str,
    *,
    competition_code: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    db.execute(
        """
        INSERT OR IGNORE INTO career_calendar_events(
            career_id, season_number, week, event_type, title, description,
            competition_code, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            career_id,
            season_number,
            week,
            event_type,
            title,
            description,
            competition_code,
            json.dumps(payload or {}, sort_keys=True),
        ),
    )


def generate_season_calendar(
    db,
    career_id: int,
    season_number: int,
    season_label: str,
    league_id: int,
    *,
    preserve_completed: bool = False,
) -> None:
    """Build a deterministic 52-week calendar and map league rounds onto it."""
    start = first_monday_of_july(season_start_year(season_label))
    country = db.execute(
        """
        SELECT co.confederation FROM leagues l
        JOIN countries co ON co.id=l.country_id WHERE l.id=?
        """,
        (league_id,),
    ).fetchone()
    confederation = country["confederation"] if country else ""
    tournament = tournament_for_season(season_label, confederation)

    existing_status: dict[int, str] = {}
    if preserve_completed:
        existing_status = {
            row["week"]: row["status"]
            for row in db.execute(
                "SELECT week, status FROM career_calendar_weeks WHERE career_id=? AND season_number=?",
                (career_id, season_number),
            ).fetchall()
        }
    db.execute(
        "DELETE FROM career_calendar_events WHERE career_id=? AND season_number=?",
        (career_id, season_number),
    )
    db.execute(
        "DELETE FROM career_calendar_weeks WHERE career_id=? AND season_number=?",
        (career_id, season_number),
    )

    for week in range(1, 53):
        week_start = start + timedelta(days=(week - 1) * 7)
        week_end = week_start + timedelta(days=6)
        phase = _phase_for_week(week)
        window = INTERNATIONAL_WINDOWS.get(week)
        headline = {
            "offseason": "Close-season week",
            "preseason": "Pre-season programme",
            "competitive": "Club season",
            "international_finals": "International finals and club finals",
        }[phase]
        if window:
            headline = window[1]
        if tournament and week >= 49:
            headline = tournament
        db.execute(
            """
            INSERT INTO career_calendar_weeks(
                career_id, season_number, week, start_date, end_date, phase,
                headline, is_transfer_window, is_international_window, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                career_id,
                season_number,
                week,
                week_start.isoformat(),
                week_end.isoformat(),
                phase,
                headline,
                int(week in TRANSFER_WEEKS),
                int(bool(window) or bool(tournament and week >= 49)),
                existing_status.get(week, "upcoming"),
            ),
        )

    rounds = [
        row["week"]
        for row in db.execute(
            """
            SELECT DISTINCT week FROM fixtures
            WHERE career_id=? AND season_number=? AND league_id=? AND stage='league'
            ORDER BY week
            """,
            (career_id, season_number, league_id),
        ).fetchall()
    ]
    calendar_weeks = _league_calendar_weeks(len(rounds))
    for round_number, calendar_week in zip(rounds, calendar_weeks):
        week_start = start + timedelta(days=(calendar_week - 1) * 7)
        kickoff = week_start + timedelta(days=5)
        db.execute(
            """
            UPDATE fixtures SET calendar_week=?, kickoff_date=?
            WHERE career_id=? AND season_number=? AND league_id=? AND week=?
            """,
            (calendar_week, kickoff.isoformat(), career_id, season_number, league_id, round_number),
        )
        _add_event(
            db,
            career_id,
            season_number,
            calendar_week,
            "league_round",
            f"League round {round_number}",
            "The active league plays a full round of fixtures.",
            payload={"round": round_number, "league_id": league_id},
        )

    for week, (_kind, label) in INTERNATIONAL_WINDOWS.items():
        competition = "UEFA Nations League" if nations_league_active(season_label, confederation) and week in {14, 15, 21} else "International programme"
        _add_event(
            db,
            career_id,
            season_number,
            week,
            "international_window",
            competition,
            f"{label}. Call-ups, qualifiers, Nations League matches or friendlies are resolved here.",
            competition_code="UNL" if competition == "UEFA Nations League" else None,
        )

    if tournament:
        for week in range(49, 53):
            _add_event(
                db,
                career_id,
                season_number,
                week,
                "international_tournament",
                tournament,
                "National-team final tournament week. Selected players remain on international duty.",
                payload={"tournament": tournament, "tournament_week": week - 48},
            )

    for week in sorted(TRANSFER_WEEKS):
        _add_event(
            db,
            career_id,
            season_number,
            week,
            "transfer_window",
            "Transfer market open",
            "Agents, clubs and contract teams can negotiate during this week.",
        )

    for week in (1, 2, 3, 51, 52):
        _add_event(
            db,
            career_id,
            season_number,
            week,
            "offseason",
            "Player programme",
            "Choose rest, holiday, individual work, commercial duty, charity or an agent meeting.",
        )

    # The wider competition calendar is visible even while full playable cup
    # brackets remain a separate engine concern.
    domestic_weeks = (12, 19, 28, 35, 42, 48)
    for index, week in enumerate(domestic_weeks, start=1):
        _add_event(
            db,
            career_id,
            season_number,
            week,
            "domestic_cup",
            "Domestic cup programme",
            f"National cup round {index}; the world engine records background progress.",
        )

    entries = db.execute(
        """
        SELECT cp.code, cp.name FROM competition_entries ce
        JOIN competitions cp ON cp.id=ce.competition_id
        WHERE ce.career_id=? AND ce.season_number=? AND ce.club_id=(SELECT club_id FROM careers WHERE id=?)
        ORDER BY cp.reputation DESC
        """,
        (career_id, season_number, career_id),
    ).fetchall()
    continental_weeks = (10, 13, 17, 22, 27, 32, 38, 43, 47, 49)
    for entry in entries:
        for index, week in enumerate(continental_weeks, start=1):
            _add_event(
                db,
                career_id,
                season_number,
                week,
                "continental",
                entry["name"],
                f"Continental match slot {index} for qualified clubs.",
                competition_code=entry["code"],
            )


def get_calendar(db, career_id: int, season_number: int) -> list[dict[str, Any]]:
    weeks = db.execute(
        """
        SELECT * FROM career_calendar_weeks
        WHERE career_id=? AND season_number=? ORDER BY week
        """,
        (career_id, season_number),
    ).fetchall()
    events = db.execute(
        """
        SELECT * FROM career_calendar_events
        WHERE career_id=? AND season_number=? ORDER BY week, id
        """,
        (career_id, season_number),
    ).fetchall()
    by_week: dict[int, list[Any]] = {}
    for event in events:
        by_week.setdefault(event["week"], []).append(event)
    return [{**dict(week), "events": by_week.get(week["week"], [])} for week in weeks]


def get_week_context(db, career) -> dict[str, Any]:
    week_number = int(career["calendar_week"] or 1)
    week = db.execute(
        """
        SELECT * FROM career_calendar_weeks
        WHERE career_id=? AND season_number=? AND week=?
        """,
        (career["id"], career["season_number"], week_number),
    ).fetchone()
    events = db.execute(
        """
        SELECT * FROM career_calendar_events
        WHERE career_id=? AND season_number=? AND week=? ORDER BY id
        """,
        (career["id"], career["season_number"], week_number),
    ).fetchall()
    next_fixture = db.execute(
        """
        SELECT f.*, h.name AS home_name, a.name AS away_name
        FROM fixtures f JOIN clubs h ON h.id=f.home_club_id JOIN clubs a ON a.id=f.away_club_id
        WHERE f.career_id=? AND f.season_number=? AND f.played=0
          AND (f.home_club_id=? OR f.away_club_id=?)
        ORDER BY COALESCE(f.calendar_week, 999), f.week, f.id LIMIT 1
        """,
        (career["id"], career["season_number"], career["club_id"], career["club_id"]),
    ).fetchone()
    fixtures_this_week = db.execute(
        """
        SELECT f.*, h.name AS home_name, a.name AS away_name
        FROM fixtures f JOIN clubs h ON h.id=f.home_club_id JOIN clubs a ON a.id=f.away_club_id
        WHERE f.career_id=? AND f.season_number=? AND f.played=0 AND f.calendar_week=?
          AND (f.home_club_id=? OR f.away_club_id=?)
        ORDER BY f.week, f.id
        """,
        (career["id"], career["season_number"], week_number, career["club_id"], career["club_id"]),
    ).fetchall()
    return {
        "week": week,
        "events": events,
        "next_fixture": next_fixture,
        "fixtures_this_week": fixtures_this_week,
        "can_play": bool(fixtures_this_week),
        "can_advance": not fixtures_this_week and week_number <= 52,
        "calendar_complete": week_number > 52,
    }
