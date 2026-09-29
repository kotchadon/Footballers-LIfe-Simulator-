"""Public, pre-kickoff identity projection. Never include sealed match outcomes."""


def cockpit_context(plan):
    plan = plan or {}
    fields = ("actor_id", "display_name", "shirt_number", "role", "team")

    def identity(actor):
        return {key: actor.get(key) for key in fields}

    career = plan.get("career_player", {})
    return {
        "player": identity(career.get("actor") or career),
        "selection": career.get("selection_status", "bench"),
        "squads": {
            side: [identity(actor) for actor in plan.get("actors", []) if actor.get("team") == side]
            for side in ("home", "away")
        },
        "bench_complete": False,
    }
