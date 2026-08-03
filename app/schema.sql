CREATE TABLE IF NOT EXISTS clubs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    short_name TEXT NOT NULL UNIQUE,
    strength INTEGER NOT NULL,
    reputation INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS careers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_name TEXT NOT NULL,
    nationality TEXT NOT NULL,
    position TEXT NOT NULL,
    age INTEGER NOT NULL DEFAULT 16,
    overall INTEGER NOT NULL DEFAULT 52,
    potential INTEGER NOT NULL DEFAULT 88,
    fitness INTEGER NOT NULL DEFAULT 100,
    morale INTEGER NOT NULL DEFAULT 70,
    reputation INTEGER NOT NULL DEFAULT 5,
    money INTEGER NOT NULL DEFAULT 0,
    wage INTEGER NOT NULL DEFAULT 450,
    xp INTEGER NOT NULL DEFAULT 0,
    current_week INTEGER NOT NULL DEFAULT 1,
    season_number INTEGER NOT NULL DEFAULT 1,
    season_label TEXT NOT NULL DEFAULT '2026/27',
    weekly_action_used INTEGER NOT NULL DEFAULT 0,
    training_focus TEXT NOT NULL DEFAULT 'balanced',
    injured_weeks INTEGER NOT NULL DEFAULT 0,
    suspended_matches INTEGER NOT NULL DEFAULT 0,
    yellow_card_accumulation INTEGER NOT NULL DEFAULT 0,
    club_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (club_id) REFERENCES clubs(id)
);

CREATE TABLE IF NOT EXISTS player_attributes (
    career_id INTEGER PRIMARY KEY,
    pace INTEGER NOT NULL DEFAULT 50,
    shooting INTEGER NOT NULL DEFAULT 50,
    passing INTEGER NOT NULL DEFAULT 50,
    dribbling INTEGER NOT NULL DEFAULT 50,
    defending INTEGER NOT NULL DEFAULT 50,
    physical INTEGER NOT NULL DEFAULT 50,
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS fixtures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL DEFAULT 1,
    week INTEGER NOT NULL,
    home_club_id INTEGER NOT NULL,
    away_club_id INTEGER NOT NULL,
    played INTEGER NOT NULL DEFAULT 0,
    home_goals INTEGER,
    away_goals INTEGER,
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY (home_club_id) REFERENCES clubs(id),
    FOREIGN KEY (away_club_id) REFERENCES clubs(id)
);

CREATE TABLE IF NOT EXISTS standings (
    career_id INTEGER NOT NULL,
    club_id INTEGER NOT NULL,
    played INTEGER NOT NULL DEFAULT 0,
    won INTEGER NOT NULL DEFAULT 0,
    drawn INTEGER NOT NULL DEFAULT 0,
    lost INTEGER NOT NULL DEFAULT 0,
    goals_for INTEGER NOT NULL DEFAULT 0,
    goals_against INTEGER NOT NULL DEFAULT 0,
    points INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (career_id, club_id),
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY (club_id) REFERENCES clubs(id)
);

CREATE TABLE IF NOT EXISTS player_stats (
    career_id INTEGER PRIMARY KEY,
    appearances INTEGER NOT NULL DEFAULT 0,
    starts INTEGER NOT NULL DEFAULT 0,
    sub_appearances INTEGER NOT NULL DEFAULT 0,
    minutes INTEGER NOT NULL DEFAULT 0,
    goals INTEGER NOT NULL DEFAULT 0,
    assists INTEGER NOT NULL DEFAULT 0,
    yellow_cards INTEGER NOT NULL DEFAULT 0,
    red_cards INTEGER NOT NULL DEFAULT 0,
    injuries INTEGER NOT NULL DEFAULT 0,
    matches_missed_injury INTEGER NOT NULL DEFAULT 0,
    matches_missed_suspension INTEGER NOT NULL DEFAULT 0,
    motm INTEGER NOT NULL DEFAULT 0,
    rating_total REAL NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    draws INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS season_player_stats (
    career_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    season_label TEXT NOT NULL,
    club_id INTEGER NOT NULL,
    appearances INTEGER NOT NULL DEFAULT 0,
    starts INTEGER NOT NULL DEFAULT 0,
    sub_appearances INTEGER NOT NULL DEFAULT 0,
    minutes INTEGER NOT NULL DEFAULT 0,
    goals INTEGER NOT NULL DEFAULT 0,
    assists INTEGER NOT NULL DEFAULT 0,
    yellow_cards INTEGER NOT NULL DEFAULT 0,
    red_cards INTEGER NOT NULL DEFAULT 0,
    motm INTEGER NOT NULL DEFAULT 0,
    rating_total REAL NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    draws INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (career_id, season_number),
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY (club_id) REFERENCES clubs(id)
);

CREATE TABLE IF NOT EXISTS match_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL DEFAULT 1,
    week INTEGER NOT NULL,
    fixture_id INTEGER NOT NULL,
    player_started INTEGER NOT NULL,
    selection_status TEXT NOT NULL DEFAULT 'starter',
    player_minutes INTEGER NOT NULL DEFAULT 0,
    player_goals INTEGER NOT NULL DEFAULT 0,
    player_assists INTEGER NOT NULL DEFAULT 0,
    player_yellow_cards INTEGER NOT NULL DEFAULT 0,
    player_red_cards INTEGER NOT NULL DEFAULT 0,
    player_injured INTEGER NOT NULL DEFAULT 0,
    player_rating REAL NOT NULL,
    player_motm INTEGER NOT NULL DEFAULT 0,
    commentary TEXT NOT NULL,
    development_summary TEXT NOT NULL DEFAULT '',
    fitness_before INTEGER NOT NULL DEFAULT 100,
    fitness_after INTEGER NOT NULL DEFAULT 100,
    session_id INTEGER,
    events_json TEXT NOT NULL DEFAULT '[]',
    metrics_json TEXT NOT NULL DEFAULT '{}',
    analysis_json TEXT NOT NULL DEFAULT '{}',
    finalized_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY (fixture_id) REFERENCES fixtures(id)
);


CREATE TABLE IF NOT EXISTS match_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_id TEXT NOT NULL UNIQUE,
    career_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    week INTEGER NOT NULL,
    player_fixture_id INTEGER NOT NULL,
    seed INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'prepared' CHECK(status IN ('prepared', 'completed', 'void')),
    revealed_event_count INTEGER NOT NULL DEFAULT 0,
    event_count INTEGER NOT NULL,
    simulation_json TEXT NOT NULL,
    report_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    UNIQUE(career_id, season_number, week),
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY (player_fixture_id) REFERENCES fixtures(id)
);

CREATE TABLE IF NOT EXISTS season_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    season_label TEXT NOT NULL,
    club_id INTEGER NOT NULL,
    league_position INTEGER NOT NULL,
    league_points INTEGER NOT NULL,
    appearances INTEGER NOT NULL,
    goals INTEGER NOT NULL,
    assists INTEGER NOT NULL,
    average_rating REAL NOT NULL,
    awards TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(career_id, season_number),
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY (club_id) REFERENCES clubs(id)
);

CREATE TABLE IF NOT EXISTS transfer_offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    from_club_id INTEGER NOT NULL,
    to_club_id INTEGER NOT NULL,
    wage INTEGER NOT NULL,
    signing_bonus INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY (from_club_id) REFERENCES clubs(id),
    FOREIGN KEY (to_club_id) REFERENCES clubs(id)
);

CREATE TABLE IF NOT EXISTS club_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career_id INTEGER NOT NULL,
    club_id INTEGER NOT NULL,
    joined_season INTEGER NOT NULL,
    left_season INTEGER,
    reason TEXT NOT NULL DEFAULT 'Signed',
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY (club_id) REFERENCES clubs(id)
);

CREATE TABLE IF NOT EXISTS finance_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    week INTEGER NOT NULL,
    category TEXT NOT NULL,
    amount INTEGER NOT NULL,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE
);


