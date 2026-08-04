import sqlite3
from pathlib import Path

from flask import current_app, g


CAREER_COLUMNS = {
    "wage": "INTEGER NOT NULL DEFAULT 450",
    "xp": "INTEGER NOT NULL DEFAULT 0",
    "season_number": "INTEGER NOT NULL DEFAULT 1",
    "weekly_action_used": "INTEGER NOT NULL DEFAULT 0",
    "training_focus": "TEXT NOT NULL DEFAULT 'balanced'",
    "injured_weeks": "INTEGER NOT NULL DEFAULT 0",
    "suspended_matches": "INTEGER NOT NULL DEFAULT 0",
    "yellow_card_accumulation": "INTEGER NOT NULL DEFAULT 0",
    "league_id": "INTEGER",
    "squad_level": "TEXT NOT NULL DEFAULT 'first_team'",
    "manager_trust": "INTEGER NOT NULL DEFAULT 35",
    "pathway_status": "TEXT NOT NULL DEFAULT 'senior_development'",
}

PLAYER_STATS_COLUMNS = {
    "sub_appearances": "INTEGER NOT NULL DEFAULT 0",
    "minutes": "INTEGER NOT NULL DEFAULT 0",
    "injuries": "INTEGER NOT NULL DEFAULT 0",
    "matches_missed_injury": "INTEGER NOT NULL DEFAULT 0",
    "matches_missed_suspension": "INTEGER NOT NULL DEFAULT 0",
}

FIXTURE_COLUMNS = {
    "season_number": "INTEGER NOT NULL DEFAULT 1",
    "league_id": "INTEGER",
    "competition_id": "INTEGER",
    "stage": "TEXT NOT NULL DEFAULT 'league'",
    "round_label": "TEXT NOT NULL DEFAULT ''",
}

CLUB_COLUMNS = {
    "country_id": "INTEGER",
    "league_id": "INTEGER",
    "youth_rating": "INTEGER NOT NULL DEFAULT 50",
    "reserve_rating": "INTEGER NOT NULL DEFAULT 50",
    "is_real": "INTEGER NOT NULL DEFAULT 1",
}

STANDINGS_COLUMNS = {
    "league_id": "INTEGER",
    "season_number": "INTEGER NOT NULL DEFAULT 1",
}

TRANSFER_COLUMNS = {"to_league_id": "INTEGER"}
SEASON_HISTORY_COLUMNS = {"league_id": "INTEGER"}

MATCH_REPORT_COLUMNS = {
    "season_number": "INTEGER NOT NULL DEFAULT 1",
    "selection_status": "TEXT NOT NULL DEFAULT 'starter'",
    "player_minutes": "INTEGER NOT NULL DEFAULT 0",
    "player_yellow_cards": "INTEGER NOT NULL DEFAULT 0",
    "player_red_cards": "INTEGER NOT NULL DEFAULT 0",
    "player_injured": "INTEGER NOT NULL DEFAULT 0",
    "development_summary": "TEXT NOT NULL DEFAULT ''",
    "fitness_before": "INTEGER NOT NULL DEFAULT 100",
    "fitness_after": "INTEGER NOT NULL DEFAULT 100",
    "session_id": "INTEGER",
    "events_json": "TEXT NOT NULL DEFAULT '[]'",
    "metrics_json": "TEXT NOT NULL DEFAULT '{}'",
    "analysis_json": "TEXT NOT NULL DEFAULT '{}'",
    "finalized_at": "TEXT",
}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _column_names(db, table):
    return {row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}


def _add_missing_columns(db, table, definitions):
    existing = _column_names(db, table)
    for name, definition in definitions.items():
        if name not in existing:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def migrate_existing_save(db):
    """Add newer fields without deleting an existing V1/V2 career save."""
    _add_missing_columns(db, "clubs", CLUB_COLUMNS)
    _add_missing_columns(db, "careers", CAREER_COLUMNS)
    _add_missing_columns(db, "player_stats", PLAYER_STATS_COLUMNS)
    _add_missing_columns(db, "fixtures", FIXTURE_COLUMNS)
    _add_missing_columns(db, "standings", STANDINGS_COLUMNS)
    _add_missing_columns(db, "transfer_offers", TRANSFER_COLUMNS)
    _add_missing_columns(db, "season_history", SEASON_HISTORY_COLUMNS)
    _add_missing_columns(db, "match_reports", MATCH_REPORT_COLUMNS)
    db.execute(
        "UPDATE player_stats SET minutes = starts * 90 WHERE minutes = 0 AND appearances > 0"
    )
    db.execute(
        "UPDATE careers SET training_focus = 'balanced' WHERE training_focus IS NULL OR training_focus = ''"
    )

    careers = db.execute("SELECT * FROM careers").fetchall()
    for career in careers:
        career_id = career["id"]
        season_number = career["season_number"]

        existing_attributes = db.execute(
            "SELECT 1 FROM player_attributes WHERE career_id = ?", (career_id,)
        ).fetchone()
        if existing_attributes is None:
            base = max(40, min(75, career["overall"]))
            db.execute(
                """
                INSERT INTO player_attributes(
                    career_id, pace, shooting, passing, dribbling, defending, physical
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (career_id, base, base, base, base, base, base),
            )

        season_row = db.execute(
            "SELECT 1 FROM season_player_stats WHERE career_id = ? AND season_number = ?",
            (career_id, season_number),
        ).fetchone()
        if season_row is None:
            stats = db.execute(
                "SELECT * FROM player_stats WHERE career_id = ?", (career_id,)
            ).fetchone()
            if stats is not None:
                db.execute(
                    """
                    INSERT INTO season_player_stats(
                        career_id, season_number, season_label, club_id,
                        appearances, starts, sub_appearances, minutes, goals, assists,
                        yellow_cards, red_cards, motm, rating_total, wins, draws, losses
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        career_id,
                        season_number,
                        career["season_label"],
                        career["club_id"],
                        stats["appearances"],
                        stats["starts"],
                        stats["sub_appearances"],
                        stats["minutes"],
                        stats["goals"],
                        stats["assists"],
                        stats["yellow_cards"],
                        stats["red_cards"],
                        stats["motm"],
                        stats["rating_total"],
                        stats["wins"],
                        stats["draws"],
                        stats["losses"],
                    ),
                )

        history_row = db.execute(
            "SELECT 1 FROM club_history WHERE career_id = ?", (career_id,)
        ).fetchone()
        if history_row is None and career["club_id"] is not None:
            db.execute(
                "INSERT INTO club_history(career_id, club_id, joined_season, reason) VALUES (?, ?, ?, ?)",
                (career_id, career["club_id"], season_number, "Academy graduate"),
            )

    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_fixtures_career_season_week ON fixtures(career_id, season_number, week)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_reports_career_season ON match_reports(career_id, season_number)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_match_sessions_career_status ON match_sessions(career_id, status)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_match_sessions_public_id ON match_sessions(public_id)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_clubs_league ON clubs(league_id, strength, reputation)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_world_memberships_league ON world_memberships(career_id, season_number, league_id)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_awards_career_season ON career_awards(career_id, season_number)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_competition_entries_season ON competition_entries(career_id, season_number, competition_id)"
    )
    db.commit()


def init_db():
    db = get_db()
    schema_path = Path(__file__).with_name("schema.sql")
    db.executescript(schema_path.read_text())
    migrate_existing_save(db)
    from .world import seed_world_database, migrate_legacy_world
    seed_world_database(db)
    migrate_legacy_world(db)
    db.commit()
