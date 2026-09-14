from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from .services import (
    accept_endorsement,
    accept_transfer_offer,
    advance_calendar_week,
    advance_match_session,
    buy_investment,
    buy_property,
    complete_match_session,
    create_career,
    decline_endorsement,
    decline_transfer_offer,
    finalize_season,
    get_active_career,
    get_active_match_session,
    get_calendar_context,
    get_calendar_dashboard,
    get_career_awards,
    get_career_command_center,
    get_club_history,
    get_competition_entries,
    get_competition_honours,
    get_current_league,
    get_finances,
    get_financial_dashboard,
    get_international_summary,
    get_market_dashboard,
    get_match_session_view,
    get_next_player_fixture,
    get_pending_transfer_offers,
    get_recent_reports,
    get_season_history,
    get_season_stats,
    get_standings,
    get_stats,
    get_training_plan,
    get_world_league,
    get_world_overview,
    place_virtual_wager,
    prepare_next_match,
    recover_player,
    request_agent_market_search,
    season_is_complete,
    sell_investment,
    set_training_focus,
    start_next_season,
    take_offseason_action,
    train_player,
)
from .player_visuals import build_player_visual

bp = Blueprint("main", __name__)


@bp.context_processor
def inject_career_shell():
    career = get_active_career()
    if career is None:
        return {"career_shell": None}
    return {"career_shell": get_career_command_center(career["id"])}


@bp.get("/api/career-state")
def career_state_api():
    career = get_active_career()
    if career is None:
        return jsonify({"ok": False, "message": "Create a career first."}), 404
    return jsonify({"ok": True, "state": get_career_command_center(career["id"])})


@bp.after_app_request
def disable_dynamic_cache(response):
    if request.path.startswith(("/match/", "/api/matches/", "/api/career-state", "/finances", "/market", "/calendar")):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


def _active_or_new():
    career = get_active_career()
    return career, None if career else redirect(url_for("main.new_career"))


def _int_field(name, default=0):
    try:
        return int(request.form.get(name, default))
    except (TypeError, ValueError):
        return int(default)


@bp.get("/")
def index():
    career = get_active_career()
    if career is None:
        return render_template("welcome.html")
    active_match = get_active_match_session(career["id"])
    context = get_calendar_context(career)
    finance = get_financial_dashboard(career["id"])
    international = get_international_summary(career["id"])
    market = get_market_dashboard(career["id"])
    return render_template(
        "dashboard.html",
        career=career,
        player_visual_model=build_player_visual(career, context="dashboard"),
        fixture=get_next_player_fixture(career),
        active_match=active_match,
        standings=get_standings(career["id"]),
        stats=get_stats(career["id"]),
        season_stats=get_season_stats(career["id"], career["season_number"]),
        reports=get_recent_reports(career["id"]),
        offers=get_pending_transfer_offers(career["id"]),
        training_plan=get_training_plan(career["id"]),
        season_complete=season_is_complete(career),
        current_league=get_current_league(career),
        awards=get_career_awards(career["id"], limit=8),
        continental_entries=get_competition_entries(career["id"]),
        calendar_context=context,
        finance=finance,
        international=international,
        market=market,
    )


@bp.route("/new-career", methods=["GET", "POST"])
def new_career():
    if request.method == "POST":
        name = request.form.get("player_name", "").strip()
        nationality = request.form.get("nationality", "").strip()
        position = request.form.get("position", "ST")
        if not name or not nationality:
            flash("Player name and nationality are required.")
        else:
            create_career(name, nationality, position)
            return redirect(url_for("main.index"))
    return render_template("new_career.html")


@bp.post("/play")
def play():
    career, redirect_response = _active_or_new()
    if redirect_response:
        return redirect_response
    context = get_calendar_context(career)
    if not context or not context["can_play"]:
        flash("There is no club fixture in the current calendar week. Advance the calendar instead.")
        return redirect(url_for("main.index"))
    session = prepare_next_match(career["id"])
    if session is None:
        flash("No playable club match is available in this week.")
        return redirect(url_for("main.index"))
    return redirect(url_for("main.match_centre", session_id=session["public_id"]), code=303)


@bp.get("/match/<session_id>")
def match_centre(session_id):
    career, redirect_response = _active_or_new()
    if redirect_response:
        return redirect_response
    session = get_match_session_view(session_id, career["id"])
    if session is None:
        flash("That match session does not exist for the active career.")
        return redirect(url_for("main.index"))
    return render_template("match.html", career=career, session=session)


@bp.post("/api/matches/<session_id>/advance")
def advance_match_api(session_id):
    career = get_active_career()
    if career is None:
        return jsonify({"ok": False, "message": "Create a career first."}), 404
    payload = request.get_json(silent=True) or {}
    success, message, data = advance_match_session(session_id, career["id"], payload.get("cursor", 0))
    return jsonify({"ok": success, "message": message, **(data or {})}), 200 if success else 409


@bp.post("/api/matches/<session_id>/complete")
def complete_match_api(session_id):
    career = get_active_career()
    if career is None:
        return jsonify({"ok": False, "message": "Create a career first."}), 404
    payload = request.get_json(silent=True) or {}
    success, message, data = complete_match_session(session_id, career["id"], allow_skip=bool(payload.get("skip", False)))
    response = {"ok": success, "message": message, **(data or {})}
    if success:
        response["dashboard_url"] = url_for("main.index")
    return jsonify(response), 200 if success else 409


@bp.post("/api/training-plan")
def training_plan_api():
    career = get_active_career()
    if career is None:
        return jsonify({"ok": False, "message": "Create a career first."}), 404
    payload = request.get_json(silent=True) or request.form
    focus = str(payload.get("focus", "")).strip().lower()
    success, message, plan = set_training_focus(career["id"], focus)
    status = 200 if success else 409 if "active match" in message.lower() else 400
    return jsonify({"ok": success, "message": message, "plan": plan}), status


@bp.post("/recover")
def recover():
    career = get_active_career()
    if career:
        _success, message = recover_player(career["id"])
        flash(message)
    return redirect(url_for("main.index") + "#development")


@bp.post("/train")
def train():
    career = get_active_career()
    if career:
        _success, message = train_player(career["id"], request.form.get("focus", ""))
        flash(message)
    return redirect(url_for("main.index") + "#development")


@bp.post("/calendar/advance")
def calendar_advance():
    career = get_active_career()
    if career:
        _success, message, _data = advance_calendar_week(career["id"])
        flash(message)
    return redirect(request.form.get("next") or url_for("main.index"))


@bp.get("/calendar")
def calendar_view():
    career, redirect_response = _active_or_new()
    if redirect_response:
        return redirect_response
    return render_template(
        "calendar.html",
        career=career,
        calendar=get_calendar_dashboard(career["id"]),
        international=get_international_summary(career["id"]),
        season_complete=season_is_complete(career),
    )


@bp.post("/end-season")
def end_season():
    career = get_active_career()
    if career:
        _success, message = finalize_season(career["id"])
        flash(message)
    return redirect(request.form.get("next") or url_for("main.index"))


@bp.post("/season/start")
def season_start():
    career = get_active_career()
    if career:
        _success, message = start_next_season(career["id"])
        flash(message)
    return redirect(request.form.get("next") or url_for("main.index"))


@bp.post("/offseason/action")
def offseason_action():
    career = get_active_career()
    if career:
        _success, message = take_offseason_action(career["id"], request.form.get("action", ""))
        flash(message)
    return redirect(request.form.get("next") or url_for("main.calendar_view"))


@bp.get("/market")
def market_view():
    career, redirect_response = _active_or_new()
    if redirect_response:
        return redirect_response
    return render_template("market.html", career=career, market=get_market_dashboard(career["id"]))


@bp.post("/market/agent-search")
def market_agent_search():
    career = get_active_career()
    if career:
        _success, message, _count = request_agent_market_search(career["id"])
        flash(message)
    return redirect(url_for("main.market_view"))


@bp.post("/transfer/<int:offer_id>/accept")
def accept_transfer(offer_id):
    career = get_active_career()
    if career:
        _success, message = accept_transfer_offer(career["id"], offer_id)
        flash(message)
    return redirect(url_for("main.market_view"))


@bp.post("/transfer/<int:offer_id>/decline")
def decline_transfer(offer_id):
    career = get_active_career()
    if career:
        declined = decline_transfer_offer(career["id"], offer_id)
        flash("Offer declined." if declined else "Offer is no longer available.")
    return redirect(url_for("main.market_view"))


@bp.get("/finances")
def finances_view():
    career, redirect_response = _active_or_new()
    if redirect_response:
        return redirect_response
    return render_template("finances.html", career=career, finance=get_financial_dashboard(career["id"]))


@bp.post("/endorsement/<int:endorsement_id>/accept")
def endorsement_accept(endorsement_id):
    career = get_active_career()
    if career:
        _success, message = accept_endorsement(career["id"], endorsement_id)
        flash(message)
    return redirect(url_for("main.finances_view") + "#endorsements")


@bp.post("/endorsement/<int:endorsement_id>/decline")
def endorsement_decline(endorsement_id):
    career = get_active_career()
    if career:
        success = decline_endorsement(career["id"], endorsement_id)
        flash("Endorsement declined." if success else "Offer is no longer available.")
    return redirect(url_for("main.finances_view") + "#endorsements")


@bp.post("/investments/<int:instrument_id>/buy")
def investment_buy(instrument_id):
    career = get_active_career()
    if career:
        _success, message = buy_investment(career["id"], instrument_id, _int_field("amount"))
        flash(message)
    return redirect(url_for("main.finances_view") + "#investments")


@bp.post("/investments/<int:instrument_id>/sell")
def investment_sell(instrument_id):
    career = get_active_career()
    if career:
        _success, message = sell_investment(career["id"], instrument_id, _int_field("percent", 25))
        flash(message)
    return redirect(url_for("main.finances_view") + "#investments")


@bp.post("/properties/<int:property_id>/buy")
def property_buy(property_id):
    career = get_active_career()
    if career:
        _success, message = buy_property(career["id"], property_id)
        flash(message)
    return redirect(url_for("main.finances_view") + "#property")


@bp.post("/wager")
def wager():
    career = get_active_career()
    if career:
        _success, message = place_virtual_wager(career["id"], _int_field("stake"), request.form.get("risk", "balanced"))
        flash(message)
    return redirect(url_for("main.finances_view") + "#virtual-wager")


@bp.get("/career-history")
def career_history():
    career, redirect_response = _active_or_new()
    if redirect_response:
        return redirect_response
    return render_template(
        "history.html",
        career=career,
        stats=get_stats(career["id"]),
        seasons=get_season_history(career["id"]),
        clubs=get_club_history(career["id"]),
        finances=get_finances(career["id"]),
        awards=get_career_awards(career["id"]),
        honours=get_competition_honours(career["id"]),
        international=get_international_summary(career["id"]),
    )


@bp.get("/world")
def world():
    career, redirect_response = _active_or_new()
    if redirect_response:
        return redirect_response
    return render_template(
        "world.html", career=career, world=get_world_overview(career["id"]), selected=None,
        entries=get_competition_entries(career["id"]), honours=get_competition_honours(career["id"]),
    )


@bp.get("/world/league/<int:league_id>")
def world_league(league_id):
    career, redirect_response = _active_or_new()
    if redirect_response:
        return redirect_response
    selected = get_world_league(career["id"], league_id)
    if selected is None:
        flash("League not found.")
        return redirect(url_for("main.world"))
    return render_template(
        "world.html", career=career, world=get_world_overview(career["id"]), selected=selected,
        entries=get_competition_entries(career["id"]), honours=get_competition_honours(career["id"]),
    )

@bp.get("/api/matches/<session_id>/visual-plan")
def match_visual_plan_api(session_id):
    from .services import get_match_visual_plan

    career = get_active_career()
    if career is None:
        return jsonify({"ok": False, "message": "Create a career first."}), 404
    plan = get_match_visual_plan(session_id, career["id"])
    if plan is None:
        return jsonify({"ok": False, "message": "Match not found."}), 404
    return jsonify({"ok": True, "visual": plan})
