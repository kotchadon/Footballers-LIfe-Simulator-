from pathlib import Path
import sqlite3

import app.economy as economy
import app.services as services

ROOT = Path(__file__).resolve().parents[1]


def test_transfer_schedule_rebuild_is_blocked_after_played_fixture():
    assert hasattr(services, "_transfer_can_rebuild_current_schedule")
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE fixtures(id INTEGER PRIMARY KEY, career_id INTEGER, season_number INTEGER, played INTEGER)")
    db.execute("INSERT INTO fixtures VALUES (1,1,4,1)")
    assert services._transfer_can_rebuild_current_schedule(db, 1, 4) is False
    db.execute("DELETE FROM fixtures")
    db.execute("INSERT INTO fixtures VALUES (2,1,4,0)")
    assert services._transfer_can_rebuild_current_schedule(db, 1, 4) is True
    source = (ROOT / "app/services.py").read_text(encoding="utf-8")
    assert 'and _transfer_can_rebuild_current_schedule(' in source


def test_agent_search_does_not_consume_player_programme_choice():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("""
        CREATE TABLE careers(
            id INTEGER PRIMARY KEY, season_number INTEGER, calendar_week INTEGER,
            season_phase TEXT, money INTEGER, fitness INTEGER, morale INTEGER,
            reputation INTEGER, stress INTEGER, xp INTEGER
        )
    """)
    db.execute("""
        CREATE TABLE career_week_actions(
            id INTEGER PRIMARY KEY AUTOINCREMENT, career_id INTEGER,
            season_number INTEGER, calendar_week INTEGER, action_type TEXT,
            title TEXT, effects_json TEXT DEFAULT '{}',
            UNIQUE(career_id, season_number, calendar_week, action_type)
        )
    """)
    db.execute("INSERT INTO careers VALUES (1,4,27,'offseason',5000,72,60,20,30,4)")
    db.execute("""
        INSERT INTO career_week_actions(career_id,season_number,calendar_week,action_type,title,effects_json)
        VALUES (1,4,27,'agent_search','Agent market search','{}')
    """)
    success, message = economy.take_offseason_action(db, 1, "rest")
    assert success is True, message
    action_types = {r["action_type"] for r in db.execute("SELECT action_type FROM career_week_actions")}
    assert action_types == {"agent_search", "rest"}
    selected = economy.get_selected_player_programme(db, 1, 4, 27)
    assert selected["action_type"] == "rest"


def test_investment_position_metrics_report_personal_profit_loss():
    assert hasattr(economy, "_investment_position_metrics")
    metrics = economy._investment_position_metrics(10, 80, 92)
    assert metrics["cost_basis"] == 800.0
    assert metrics["current_value"] == 920.0
    assert metrics["gain_loss"] == 120.0
    assert metrics["gain_loss_pct"] == 15.0


def test_finance_screen_exposes_personal_profit_loss():
    template = (ROOT / "app/templates/finances.html").read_text(encoding="utf-8")
    assert "finance.investment_gain_loss" in template
    assert "item.gain_loss_pct" in template
    assert "Prices move when a career week advances" in template


def test_continue_shortcut_is_global_and_help_is_themed():
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    marker = 'if (key === "c" && document.querySelector(".keyboard-continue"))'
    assert marker in js
    assert js.index(marker) < js.index('if (page === "dashboard" && setupDashboardShortcuts(event))')
    assert "event.repeat" in js
    base = (ROOT / "app/templates/base.html").read_text(encoding="utf-8")
    assert "NAVIGATION" in base
    assert "DASHBOARD TRAINING" in base
    assert "MATCH CONTROL" in base
    theme = (ROOT / "app/static/theme-ps2.css").read_text(encoding="utf-8")
    assert "SHOWCASE SHORTCUT HARDENING" in theme
    assert ".shortcut-dialog .shortcut-grid > div" in theme
    assert ".shortcut-dialog::backdrop" in theme


def test_next_season_initialises_world_before_membership_lookup_and_fixture_build():
    source = (ROOT / "app/services.py").read_text(encoding="utf-8")
    start = source.index("def start_next_season(")
    end = source.index("\ndef get_pending_transfer_offers", start)
    block = source[start:end]
    initialise = "initialize_world_memberships(db, career_id, next_number)"
    membership = "SELECT league_id FROM world_memberships"
    build = "_create_season_world(career_id, next_number, next_league_id)"
    assert initialise in block
    assert membership in block
    assert build in block
    assert block.index(initialise) < block.index(membership) < block.index(build)


def test_command_centre_and_week_advance_use_real_player_programme_only():
    source = (ROOT / "app/services.py").read_text(encoding="utf-8")
    advance_start = source.index("def advance_calendar_week(")
    advance_end = source.index("\ndef ", advance_start + 10)
    advance = source[advance_start:advance_end]
    assert "economy_get_selected_player_programme(" in advance
    centre_start = source.index("def get_career_command_center(")
    centre = source[centre_start:]
    assert "selected_programme = economy_get_selected_player_programme(" in centre
    assert 'any(item["event_type"] == "offseason" for item in events)' in centre
    assert 'not context.get("calendar_complete")' in centre


def test_calendar_programme_ui_only_exists_on_designated_event_weeks():
    calendar = (ROOT / "app/templates/calendar.html").read_text(encoding="utf-8")
    assert "player_programme_events" in calendar
    assert "selectattr('event_type', 'equalto', 'offseason')" in calendar
    assert "not calendar.context.calendar_complete" in calendar
    assert "career.season_phase in ['offseason','preseason']" not in calendar


def test_transition_labels_never_show_week_53_of_52():
    dashboard = (ROOT / "app/templates/dashboard.html").read_text(encoding="utf-8")
    calendar = (ROOT / "app/templates/calendar.html").read_text(encoding="utf-8")
    assert "career.calendar_week > 52" in dashboard
    assert "career_shell.week > 52" in dashboard
    assert "career.calendar_week > 52" in calendar
    assert "SEASON TRANSITION" in dashboard
    assert "SEASON TRANSITION" in calendar
