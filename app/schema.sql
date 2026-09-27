CREATE TABLE IF NOT EXISTS countries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE,
    confederation TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leagues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    country_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    tier INTEGER NOT NULL,
    reputation INTEGER NOT NULL,
    team_count INTEGER NOT NULL,
    promotion_slots INTEGER NOT NULL DEFAULT 0,
    relegation_slots INTEGER NOT NULL DEFAULT 0,
    playoff_slots INTEGER NOT NULL DEFAULT 0,
    fully_playable INTEGER NOT NULL DEFAULT 1,
    rules_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(country_id, tier),
    FOREIGN KEY (country_id) REFERENCES countries(id)
);

CREATE TABLE IF NOT EXISTS competitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    country_id INTEGER,
    competition_type TEXT NOT NULL,
    confederation TEXT NOT NULL,
    reputation INTEGER NOT NULL,
    simulation_status TEXT NOT NULL DEFAULT 'catalogued',
    format_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (country_id) REFERENCES countries(id)
);

CREATE TABLE IF NOT EXISTS clubs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    short_name TEXT NOT NULL UNIQUE,
    strength INTEGER NOT NULL,
    reputation INTEGER NOT NULL,
    country_id INTEGER,
    league_id INTEGER,
    youth_rating INTEGER NOT NULL DEFAULT 50,
    reserve_rating INTEGER NOT NULL DEFAULT 50,
    is_real INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (country_id) REFERENCES countries(id),
    FOREIGN KEY (league_id) REFERENCES leagues(id)
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
    calendar_week INTEGER NOT NULL DEFAULT 1,
    season_phase TEXT NOT NULL DEFAULT 'competitive',
    season_number INTEGER NOT NULL DEFAULT 1,
    season_label TEXT NOT NULL DEFAULT '2026/27',
    weekly_action_used INTEGER NOT NULL DEFAULT 0,
    training_focus TEXT NOT NULL DEFAULT 'balanced',
    injured_weeks INTEGER NOT NULL DEFAULT 0,
    suspended_matches INTEGER NOT NULL DEFAULT 0,
    yellow_card_accumulation INTEGER NOT NULL DEFAULT 0,
    club_id INTEGER,
    league_id INTEGER,
    squad_level TEXT NOT NULL DEFAULT 'first_team',
    manager_trust INTEGER NOT NULL DEFAULT 35,
    pathway_status TEXT NOT NULL DEFAULT 'senior_development',
    national_team_reputation INTEGER NOT NULL DEFAULT 0,
    national_team_status TEXT NOT NULL DEFAULT 'uncapped',
    agent_quality INTEGER NOT NULL DEFAULT 45,
    market_value INTEGER NOT NULL DEFAULT 100000,
    lifestyle_balance INTEGER NOT NULL DEFAULT 70,
    stress INTEGER NOT NULL DEFAULT 15,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (club_id) REFERENCES clubs(id),
    FOREIGN KEY (league_id) REFERENCES leagues(id)
);

CREATE TABLE IF NOT EXISTS player_attributes (
    career_id INTEGER PRIMARY KEY,
    pace INTEGER NOT NULL DEFAULT 50,
    shooting INTEGER NOT NULL DEFAULT 50,
    passing INTEGER NOT NULL DEFAULT 50,
    dribbling INTEGER NOT NULL DEFAULT 50,
    defending INTEGER NOT NULL DEFAULT 50,
    physical INTEGER NOT NULL DEFAULT 50,
    pace_xp INTEGER NOT NULL DEFAULT 0,
    shooting_xp INTEGER NOT NULL DEFAULT 0,
    passing_xp INTEGER NOT NULL DEFAULT 0,
    dribbling_xp INTEGER NOT NULL DEFAULT 0,
    defending_xp INTEGER NOT NULL DEFAULT 0,
    physical_xp INTEGER NOT NULL DEFAULT 0,
    legacy_xp_migrated INTEGER NOT NULL DEFAULT 0,
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
    league_id INTEGER,
    competition_id INTEGER,
    stage TEXT NOT NULL DEFAULT 'league',
    round_label TEXT NOT NULL DEFAULT '',
    calendar_week INTEGER,
    kickoff_date TEXT,
    fixture_order INTEGER NOT NULL DEFAULT 1,
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
    league_id INTEGER,
    season_number INTEGER NOT NULL DEFAULT 1,
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
    league_id INTEGER,
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
    FOREIGN KEY (club_id) REFERENCES clubs(id),
    FOREIGN KEY (league_id) REFERENCES leagues(id)
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
    to_league_id INTEGER,
    offer_type TEXT NOT NULL DEFAULT 'first_team_opportunity',
    squad_role TEXT NOT NULL DEFAULT 'First-team rotation',
    contract_years INTEGER NOT NULL DEFAULT 3,
    interest_score REAL NOT NULL DEFAULT 0,
    agent_recommendation TEXT NOT NULL DEFAULT '',
    expires_calendar_week INTEGER,
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
    calendar_week INTEGER,
    category TEXT NOT NULL,
    amount INTEGER NOT NULL,
    description TEXT NOT NULL,
    reference_type TEXT,
    reference_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE
);



CREATE TABLE IF NOT EXISTS club_units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id INTEGER NOT NULL,
    unit_type TEXT NOT NULL CHECK(unit_type IN ('first_team', 'reserve', 'u18')),
    strength INTEGER NOT NULL,
    development_rating INTEGER NOT NULL,
    UNIQUE(club_id, unit_type),
    FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS world_memberships (
    career_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    club_id INTEGER NOT NULL,
    league_id INTEGER NOT NULL,
    PRIMARY KEY (career_id, season_number, club_id),
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY (club_id) REFERENCES clubs(id),
    FOREIGN KEY (league_id) REFERENCES leagues(id)
);

CREATE TABLE IF NOT EXISTS world_season_outcomes (
    career_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    league_id INTEGER NOT NULL,
    club_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    played INTEGER NOT NULL,
    won INTEGER NOT NULL,
    drawn INTEGER NOT NULL,
    lost INTEGER NOT NULL,
    goals_for INTEGER NOT NULL,
    goals_against INTEGER NOT NULL,
    points INTEGER NOT NULL,
    promoted INTEGER NOT NULL DEFAULT 0,
    relegated INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (career_id, season_number, league_id, club_id),
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY (league_id) REFERENCES leagues(id),
    FOREIGN KEY (club_id) REFERENCES clubs(id)
);

CREATE TABLE IF NOT EXISTS career_awards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    week INTEGER,
    competition_id INTEGER,
    league_id INTEGER,
    award_type TEXT NOT NULL,
    award_name TEXT NOT NULL,
    evidence_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(career_id, season_number, week, award_type, award_name),
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY (competition_id) REFERENCES competitions(id),
    FOREIGN KEY (league_id) REFERENCES leagues(id)
);

CREATE TABLE IF NOT EXISTS competition_honours (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    competition_id INTEGER NOT NULL,
    winner_club_id INTEGER,
    runner_up_club_id INTEGER,
    notes TEXT NOT NULL DEFAULT '',
    UNIQUE(career_id, season_number, competition_id),
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY (competition_id) REFERENCES competitions(id),
    FOREIGN KEY (winner_club_id) REFERENCES clubs(id),
    FOREIGN KEY (runner_up_club_id) REFERENCES clubs(id)
);


CREATE TABLE IF NOT EXISTS competition_entries (
    career_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    competition_id INTEGER NOT NULL,
    club_id INTEGER NOT NULL,
    qualification_source TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'qualified',
    PRIMARY KEY (career_id, season_number, competition_id, club_id),
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY (competition_id) REFERENCES competitions(id),
    FOREIGN KEY (club_id) REFERENCES clubs(id)
);


CREATE TABLE IF NOT EXISTS career_calendar_weeks (
    career_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    week INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    phase TEXT NOT NULL,
    headline TEXT NOT NULL,
    is_transfer_window INTEGER NOT NULL DEFAULT 0,
    is_international_window INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'upcoming',
    PRIMARY KEY (career_id, season_number, week),
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS career_calendar_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    week INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    competition_code TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'scheduled',
    UNIQUE(career_id, season_number, week, event_type, title),
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS career_week_finance (
    career_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    calendar_week INTEGER NOT NULL,
    gross_income INTEGER NOT NULL DEFAULT 0,
    total_expenses INTEGER NOT NULL DEFAULT 0,
    net_cashflow INTEGER NOT NULL DEFAULT 0,
    processed INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (career_id, season_number, calendar_week),
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS career_week_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    calendar_week INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    title TEXT NOT NULL,
    effects_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(career_id, season_number, calendar_week, action_type),
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS national_teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_id INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    short_name TEXT NOT NULL,
    confederation TEXT NOT NULL,
    rating INTEGER NOT NULL,
    reputation INTEGER NOT NULL,
    FOREIGN KEY (country_id) REFERENCES countries(id)
);

CREATE TABLE IF NOT EXISTS national_team_callups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    calendar_week INTEGER NOT NULL,
    national_team_id INTEGER NOT NULL,
    competition_name TEXT NOT NULL,
    selected INTEGER NOT NULL DEFAULT 0,
    selection_score REAL NOT NULL DEFAULT 0,
    reason TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'completed',
    appearances INTEGER NOT NULL DEFAULT 0,
    starts INTEGER NOT NULL DEFAULT 0,
    minutes INTEGER NOT NULL DEFAULT 0,
    goals INTEGER NOT NULL DEFAULT 0,
    assists INTEGER NOT NULL DEFAULT 0,
    average_rating REAL NOT NULL DEFAULT 0,
    results_json TEXT NOT NULL DEFAULT '[]',
    UNIQUE(career_id, season_number, calendar_week),
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY (national_team_id) REFERENCES national_teams(id)
);

CREATE TABLE IF NOT EXISTS international_player_stats (
    career_id INTEGER PRIMARY KEY,
    appearances INTEGER NOT NULL DEFAULT 0,
    starts INTEGER NOT NULL DEFAULT 0,
    minutes INTEGER NOT NULL DEFAULT 0,
    goals INTEGER NOT NULL DEFAULT 0,
    assists INTEGER NOT NULL DEFAULT 0,
    rating_total REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS national_team_campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    national_team_id INTEGER NOT NULL,
    competition_name TEXT NOT NULL,
    qualified INTEGER NOT NULL DEFAULT 0,
    stage TEXT NOT NULL DEFAULT 'qualification',
    points INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(career_id, season_number, national_team_id, competition_name),
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY (national_team_id) REFERENCES national_teams(id)
);

CREATE TABLE IF NOT EXISTS career_financial_profiles (
    career_id INTEGER PRIMARY KEY,
    agent_fee_rate REAL NOT NULL DEFAULT 0.05,
    tax_rate REAL NOT NULL DEFAULT 0.18,
    weekly_living_cost INTEGER NOT NULL DEFAULT 150,
    risk_profile TEXT NOT NULL DEFAULT 'balanced',
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS player_contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career_id INTEGER NOT NULL,
    club_id INTEGER NOT NULL,
    start_season INTEGER NOT NULL,
    end_season INTEGER NOT NULL,
    weekly_wage INTEGER NOT NULL,
    appearance_bonus INTEGER NOT NULL DEFAULT 0,
    goal_bonus INTEGER NOT NULL DEFAULT 0,
    assist_bonus INTEGER NOT NULL DEFAULT 0,
    signing_bonus INTEGER NOT NULL DEFAULT 0,
    squad_role TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY (club_id) REFERENCES clubs(id)
);

CREATE TABLE IF NOT EXISTS endorsements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career_id INTEGER NOT NULL,
    brand_name TEXT NOT NULL,
    category TEXT NOT NULL,
    weekly_payment INTEGER NOT NULL,
    signing_payment INTEGER NOT NULL DEFAULT 0,
    start_week INTEGER NOT NULL,
    end_week INTEGER NOT NULL,
    reputation_requirement INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS investment_instruments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    instrument_type TEXT NOT NULL,
    initial_price REAL NOT NULL,
    annual_drift REAL NOT NULL,
    volatility REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS investment_prices (
    instrument_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    calendar_week INTEGER NOT NULL,
    price REAL NOT NULL,
    PRIMARY KEY (instrument_id, season_number, calendar_week),
    FOREIGN KEY (instrument_id) REFERENCES investment_instruments(id)
);

CREATE TABLE IF NOT EXISTS investment_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career_id INTEGER NOT NULL,
    instrument_id INTEGER NOT NULL,
    units REAL NOT NULL DEFAULT 0,
    average_cost REAL NOT NULL DEFAULT 0,
    UNIQUE(career_id, instrument_id),
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY (instrument_id) REFERENCES investment_instruments(id)
);

CREATE TABLE IF NOT EXISTS property_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    purchase_price INTEGER NOT NULL,
    weekly_rent INTEGER NOT NULL DEFAULT 0,
    weekly_maintenance INTEGER NOT NULL DEFAULT 0,
    minimum_reputation INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS owned_properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career_id INTEGER NOT NULL,
    property_id INTEGER NOT NULL,
    purchase_price INTEGER NOT NULL,
    purchase_season INTEGER NOT NULL,
    purchase_week INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'owned',
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY (property_id) REFERENCES property_catalog(id)
);

CREATE TABLE IF NOT EXISTS virtual_wagers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    calendar_week INTEGER NOT NULL,
    stake INTEGER NOT NULL,
    risk_level TEXT NOT NULL,
    odds_multiplier REAL NOT NULL,
    won INTEGER NOT NULL,
    payout INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(career_id, season_number, calendar_week),
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE
);
