from flask import Blueprint, flash, redirect, render_template, request, url_for

from .services import (
    create_career,
    get_active_career,
    get_next_player_fixture,
    get_recent_reports,
    get_standings,
    get_stats,
    get_week_results,
    play_next_week,
    recover_player,
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
        reports=get_recent_reports(career["id"]),
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
    report = play_next_week(career["id"])
    if report is None:
        flash("The season is complete. Season rollover is the next feature to build.")
        return redirect(url_for("main.index"))
    return render_template(
        "match.html",
        career=career,
        report=report,
        results=get_week_results(career["id"], career["current_week"]),
    )


@bp.post("/recover")
def recover():
    career = get_active_career()
    if career:
        recover_player(career["id"])
        flash("Recovery session completed: fitness +12, morale +2.")
    return redirect(url_for("main.index"))
