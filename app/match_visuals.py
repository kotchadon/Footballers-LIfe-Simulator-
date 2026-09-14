from __future__ import annotations

import hashlib
import random
from typing import Any

VISUAL_SCHEMA_VERSION = 1

_FORMATIONS: dict[str, tuple[str, ...]] = {
    "4-3-3": ("GK", "LB", "LCB", "RCB", "RB", "DM", "LCM", "RCM", "LW", "ST", "RW"),
    "4-2-3-1": ("GK", "LB", "LCB", "RCB", "RB", "LDM", "RDM", "CAM", "LW", "ST", "RW"),
    "4-4-2": ("GK", "LB", "LCB", "RCB", "RB", "LM", "LCM", "RCM", "RM", "LST", "RST"),
    "3-5-2": ("GK", "LCB", "CB", "RCB", "LWB", "LCM", "CM", "RCM", "RWB", "LST", "RST"),
}

_FIRST_NAMES = ("Rafael", "Daniel", "Mateo", "Noah", "Elias", "Luca", "Omar", "Rayan", "Milan", "Theo", "Jay", "Kai", "Samir", "Alex", "Leo", "Nico")
_LAST_NAMES = ("Costa", "Malik", "Santos", "Lee", "Silva", "Khan", "Martin", "Garcia", "Brown", "Kim", "Rossi", "Diallo", "Meyer", "Nakamura", "Davis", "Ali")

_REQUIRED_ACTOR_KEYS = (
    "actor_id",
    "persistent_player_id",
    "display_name",
    "shirt_number",
    "role",
    "team",
    "attributes",
    "visual_profile",
)


def visual_seed(seed: int, *parts: object) -> int:
    payload = "|".join([str(int(seed)), *[str(part) for part in parts]])
    digest = hashlib.blake2b(payload.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big", signed=False)


def normalize_match_actor(actor: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "actor_id": str(actor["actor_id"]),
        "persistent_player_id": actor.get("persistent_player_id"),
        "display_name": str(actor.get("display_name") or ""),
        "shirt_number": int(actor.get("shirt_number") or 0),
        "role": str(actor.get("role") or "CM").upper(),
        "team": str(actor.get("team") or "home").lower(),
        "attributes": dict(actor.get("attributes") or {}),
        "visual_profile": dict(actor.get("visual_profile") or {}),
    }
    return {key: normalized[key] for key in _REQUIRED_ACTOR_KEYS}


def _formation_for(seed: int, side: str, strength: int, required_role: str | None = None) -> str:
    names = tuple(_FORMATIONS)
    if required_role:
        exact = tuple(name for name in names if required_role in _FORMATIONS[name])
        if exact:
            names = exact
    rng = random.Random(visual_seed(seed, "formation", side, strength, required_role or "any"))
    return names[rng.randrange(len(names))]


def _temporary_name(seed: int, team: str, index: int) -> str:
    rng = random.Random(visual_seed(seed, "name", team, index))
    first = _FIRST_NAMES[rng.randrange(len(_FIRST_NAMES))]
    last = _LAST_NAMES[rng.randrange(len(_LAST_NAMES))]
    return f"{first[0]}. {last}"


def _base_attributes(seed: int, team: str, role: str, strength: int, index: int) -> dict[str, int]:
    rng = random.Random(visual_seed(seed, "attributes", team, role, index))
    baseline = max(35, min(92, int(strength)))
    return {
        "pace": max(30, min(95, baseline + rng.randint(-10, 10))),
        "acceleration": max(30, min(95, baseline + rng.randint(-10, 10))),
        "stamina": max(30, min(95, baseline + rng.randint(-8, 12))),
        "dribbling": max(30, min(95, baseline + rng.randint(-12, 10))),
        "positioning": max(30, min(95, baseline + rng.randint(-8, 12))),
    }


def _career_attributes(snapshot: dict[str, Any]) -> dict[str, int]:
    career = dict(snapshot.get("career") or {})
    performance = dict(snapshot.get("performance") or {})
    fitness = int(performance.get("fitness_before") or career.get("fitness") or 75)
    return {
        "pace": int(career.get("pace") or 60),
        "acceleration": int(career.get("pace") or 60),
        "stamina": max(30, min(95, fitness)),
        "dribbling": int(career.get("dribbling") or 60),
        "positioning": int(career.get("passing") or 60),
        "shooting": int(career.get("shooting") or 60),
        "passing": int(career.get("passing") or 60),
        "defending": int(career.get("defending") or 50),
        "physical": int(career.get("physical") or 60),
    }


def _actors_for_team(*, seed: int, team: str, formation: str, strength: int, user: dict[str, Any] | None) -> list[dict[str, Any]]:
    roles = list(_FORMATIONS[formation])
    actors: list[dict[str, Any]] = []
    user_role = str((user or {}).get("role") or "").upper()
    user_slot = roles.index(user_role) if user and user_role in roles else None

    for index, role in enumerate(roles):
        is_user = user is not None and index == user_slot
        actor_id = str(user["actor_id"]) if is_user else f"{team}_{role.lower()}"
        attrs = dict(user.get("attributes") or {}) if is_user else _base_attributes(seed, team, role, strength, index)
        actors.append(normalize_match_actor({
            "actor_id": actor_id,
            "persistent_player_id": user.get("persistent_player_id") if is_user else None,
            "display_name": user.get("display_name") if is_user else _temporary_name(seed, team, index),
            "shirt_number": user.get("shirt_number", 17) if is_user else index + 1,
            "role": role,
            "team": team,
            "attributes": attrs,
            "visual_profile": {"is_user": bool(is_user), "kit_slot": team},
        }))
    return actors


def build_visual_plan(snapshot: dict[str, Any], seed: int) -> dict[str, Any]:
    fixture = dict(snapshot.get("fixture") or {})
    career = dict(snapshot.get("career") or {})
    performance = dict(snapshot.get("performance") or {})

    home_strength = int(fixture.get("home_strength") or fixture.get("home_team_strength") or 68)
    away_strength = int(fixture.get("away_strength") or fixture.get("away_team_strength") or 68)
    selection_status = str(performance.get("selection_status") or "starter")
    user_team = "home" if bool(fixture.get("player_team_is_home")) else "away"
    career_role = str(career.get("position") or "CM").upper()

    home_required_role = career_role if selection_status == "starter" and user_team == "home" else None
    away_required_role = career_role if selection_status == "starter" and user_team == "away" else None
    home_formation = _formation_for(seed, "home", home_strength, home_required_role)
    away_formation = _formation_for(seed, "away", away_strength, away_required_role)

    user_actor = {
        "actor_id": "career_player",
        "persistent_player_id": career.get("id"),
        "display_name": str(career.get("player_name") or "Career Player"),
        "shirt_number": 17,
        "role": career_role,
        "attributes": _career_attributes(snapshot),
    }

    home_user = user_actor if user_team == "home" and selection_status == "starter" else None
    away_user = user_actor if user_team == "away" and selection_status == "starter" else None

    actors = _actors_for_team(seed=seed, team="home", formation=home_formation, strength=home_strength, user=home_user)
    actors += _actors_for_team(seed=seed, team="away", formation=away_formation, strength=away_strength, user=away_user)

    return {
        "schema_version": VISUAL_SCHEMA_VERSION,
        "seed": int(seed),
        "home": {
            "name": str(fixture.get("home_name") or "Home"),
            "club_id": fixture.get("home_club_id"),
            "strength": home_strength,
            "formation": home_formation,
            "attacking_direction": 1,
        },
        "away": {
            "name": str(fixture.get("away_name") or "Away"),
            "club_id": fixture.get("away_club_id"),
            "strength": away_strength,
            "formation": away_formation,
            "attacking_direction": -1,
        },
        "actors": actors,
        "user_actor_id": "career_player" if selection_status == "starter" else None,
        "career_player": {
            "actor_id": "career_player",
            "selection_status": selection_status,
            "team": user_team,
            "display_name": str(career.get("player_name") or "Career Player"),
            "role": str(career.get("position") or "CM").upper(),
            "attributes": _career_attributes(snapshot),
        },
        "initial_ball": {"x": 50.0, "y": 50.0, "height": 0.0, "owner_actor_id": None, "state": "LOOSE"},
        "camera": {"mode": "broadcast_side", "keep_full_pitch_visible": True, "perspective": 0.18},
    }
