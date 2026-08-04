from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from .services import (
    accept_transfer_offer,
    advance_match_session,
    complete_match_session,
    create_career,
    decline_transfer_offer,
    finalize_season,
    get_active_career,
    get_active_match_session,
    get_club_history,
    get_career_awards,
    get_competition_entries,
    get_competition_honours,
    get_current_league,
    get_finances,
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
    prepare_next_match,
    recover_player,
    season_is_complete,
    set_training_focus,
    train_player,
)

bp = Blueprint("main", __name__)


@bp.after_app_request
def disable_match_cache(response):
    if request.path.startswith("/match/") or request.path.startswith("/api/matches/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@bp.get("/")
def index():
    career = get_active_career()
    if career is None:
        return render_template("welcome.html")
    active_match = get_active_match_session(career["id"])
    return render_template(
        "dashboard.html",
        career=career,
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
    """Prepare or resume a match, then redirect to a refresh-safe match URL."""
    career = get_active_career()
    if career is None:
        return redirect(url_for("main.new_career"))
    session = prepare_next_match(career["id"])
    if session is None:
        flash("The season is complete. Finalise it to age up and begin the next season.")
        return redirect(url_for("main.index"))
    return redirect(url_for("main.match_centre", session_id=session["public_id"]), code=303)


@bp.get("/match/<session_id>")
def match_centre(session_id):
    career = get_active_career()
    if career is None:
        return redirect(url_for("main.new_career"))
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
    status = 200 if success else 409
    return jsonify({"ok": success, "message": message, **(data or {})}), status


@bp.post("/api/matches/<session_id>/complete")
def complete_match_api(session_id):
    career = get_active_career()
    if career is None:
        return jsonify({"ok": False, "message": "Create a career first."}), 404
    payload = request.get_json(silent=True) or {}
    success, message, data = complete_match_session(
        session_id,
        career["id"],
        allow_skip=bool(payload.get("skip", False)),
    )
    status = 200 if success else 409
    response = {"ok": success, "message": message, **(data or {})}
    if success:
        response["dashboard_url"] = url_for("main.index")
    return jsonify(response), status


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


@bp.post("/end-season")
def end_season():
    career = get_active_career()
    if career:
        _success, message = finalize_season(career["id"])
        flash(message)
    return redirect(url_for("main.index"))


@bp.post("/transfer/<int:offer_id>/accept")
def accept_transfer(offer_id):
    career = get_active_career()
    if career:
        _success, message = accept_transfer_offer(career["id"], offer_id)
        flash(message)
    return redirect(url_for("main.index"))


@bp.post("/transfer/<int:offer_id>/decline")
def decline_transfer(offer_id):
    career = get_active_career()
    if career:
        declined = decline_transfer_offer(career["id"], offer_id)
        flash("Offer declined." if declined else "Offer is no longer available.")
    return redirect(url_for("main.index"))


@bp.get("/career-history")
def career_history():
    career = get_active_career()
    if career is None:
        return redirect(url_for("main.new_career"))
    return render_template(
        "history.html",
        career=career,
        stats=get_stats(career["id"]),
        seasons=get_season_history(career["id"]),
        clubs=get_club_history(career["id"]),
        finances=get_finances(career["id"]),
        awards=get_career_awards(career["id"]),
        honours=get_competition_honours(career["id"]),
    )


@bp.get("/world")
def world():
    career = get_active_career()
    if career is None:
        return redirect(url_for("main.new_career"))
    return render_template(
        "world.html",
        career=career,
        world=get_world_overview(career["id"]),
        selected=None,
        entries=get_competition_entries(career["id"]),
        honours=get_competition_honours(career["id"]),
    )


@bp.get("/world/league/<int:league_id>")
def world_league(league_id):
    career = get_active_career()
    if career is None:
        return redirect(url_for("main.new_career"))
    selected = get_world_league(career["id"], league_id)
    if selected is None:
        flash("League not found.")
        return redirect(url_for("main.world"))
    return render_template(
        "world.html",
        career=career,
        world=get_world_overview(career["id"]),
        selected=selected,
        entries=get_competition_entries(career["id"]),
        honours=get_competition_honours(career["id"]),
    )
