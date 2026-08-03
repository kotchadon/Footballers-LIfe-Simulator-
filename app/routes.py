from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from .services import (
    accept_transfer_offer,
    create_career,
    decline_transfer_offer,
    finalize_season,
    get_active_career,
    get_club_history,
    get_finances,
    get_next_player_fixture,
    get_pending_transfer_offers,
    get_recent_reports,
    get_season_history,
    get_season_stats,
    get_standings,
    get_stats,
    get_training_plan,
    get_week_results,
    play_next_week,
    recover_player,
    season_is_complete,
    set_training_focus,
    train_player,
)

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    career = get_active_career()
    if career is None:
        return render_template("welcome.html")
    return render_template(
        "dashboard.html",
        career=career,
        fixture=get_next_player_fixture(career),
        standings=get_standings(career["id"]),
        stats=get_stats(career["id"]),
        season_stats=get_season_stats(career["id"], career["season_number"]),
        reports=get_recent_reports(career["id"]),
        offers=get_pending_transfer_offers(career["id"]),
        training_plan=get_training_plan(career["id"]),
        season_complete=season_is_complete(career),
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
    career = get_active_career()
    if career is None:
        return redirect(url_for("main.new_career"))
    played_week = career["current_week"]
    played_season = career["season_number"]
    report = play_next_week(career["id"])
    if report is None:
        flash("The season is complete. Finalise it to age up and begin the next season.")
        return redirect(url_for("main.index"))
    return render_template(
        "match.html",
        career=career,
        report=report,
        results=get_week_results(career["id"], played_season, played_week),
    )


@bp.post("/api/training-plan")
def training_plan_api():
    career = get_active_career()
    if career is None:
        return jsonify({"ok": False, "message": "Create a career first."}), 404

    payload = request.get_json(silent=True) or request.form
    focus = str(payload.get("focus", "")).strip().lower()
    success, message, plan = set_training_focus(career["id"], focus)
    status = 200 if success else 400
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
    )

