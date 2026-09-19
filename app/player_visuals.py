"""Deterministic, read-only player visual identity projection.

This module deliberately contains no Flask, database, network, or gameplay
dependencies. It converts authoritative career state into a safe,
versioned visual model consumed by templates.
"""

from __future__ import annotations

import hashlib
from typing import Any

VISUAL_IDENTITY_VERSION = 1
_IDENTITY_NAMESPACE = f"footy-career-player-v{VISUAL_IDENTITY_VERSION}"

SKIN_PALETTES = (
    ("#f2c7a5", "#c88966"),
    ("#dfad86", "#ad7657"),
    ("#c98e68", "#8c5b42"),
    ("#ad704f", "#70432f"),
    ("#875238", "#543121"),
    ("#633b29", "#392218"),
)

HAIR_PALETTES = (
    ("#151313", "#3a302d"),
    ("#241914", "#5a4034"),
    ("#3b261b", "#7a5138"),
    ("#5a3b26", "#9a6a43"),
    ("#1c1d22", "#50535c"),
)

HAIR_STYLES = (
    "crop",
    "textured_crop",
    "fade",
    "short_waves",
    "side_sweep",
    "close_cut",
)

FACE_SHAPES = ("oval", "angular", "square", "long", "round")
EYE_STYLES = ("focused", "balanced", "narrow", "wide")
BROW_STYLES = ("straight", "arched", "strong", "soft")
NOSE_STYLES = ("straight", "compact", "broad", "narrow")
BUILD_STYLES = ("lean", "balanced", "athletic", "powerful")
FACIAL_HAIR_STYLES = ("clean", "clean", "stubble", "short_beard", "goatee")
KIT_PATTERNS = ("solid", "centre_panel", "vertical", "shoulder", "diagonal")

KIT_PALETTES = (
    ("#315fa8", "#dbe8ff", "#162a4a"),
    ("#8f2431", "#f2d8dc", "#421018"),
    ("#e6e8ec", "#1c2430", "#9ca8b8"),
    ("#171b25", "#e1b955", "#343d51"),
    ("#2f7d55", "#d8efe3", "#153b29"),
    ("#6a3fa0", "#eadff8", "#2e1849"),
    ("#d86b24", "#fff0df", "#65300e"),
    ("#1f7f91", "#d7f1f5", "#0d3e47"),
)

VALID_CONTEXTS = frozenset({"default", "dashboard", "match", "training"})
VALID_SELECTIONS = frozenset({"starting", "substitute", "not_selected", "unspecified"})


def _read(career: Any, key: str, default: Any = None) -> Any:
    """Read from dict/sqlite.Row-like input without requiring `.get()`."""
    if career is None:
        return default
    try:
        value = career[key]
    except (KeyError, IndexError, TypeError):
        return default
    return default if value is None else value


def _bounded_int(value: Any, default: int, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(low, min(high, number))


def _stable_index(seed: str, trait: str, option_count: int) -> int:
    if option_count <= 0:
        raise ValueError("option_count must be positive")
    payload = f"{_IDENTITY_NAMESPACE}:{seed}:{trait}".encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=8).digest()
    return int.from_bytes(digest, "big") % option_count


def _choice(seed: str, trait: str, options: tuple[Any, ...]) -> Any:
    return options[_stable_index(seed, trait, len(options))]


def _identity_key(career_id: str) -> str:
    payload = f"{_IDENTITY_NAMESPACE}:{career_id}".encode("utf-8")
    token = hashlib.blake2s(payload, digest_size=8).hexdigest()
    return f"v{VISUAL_IDENTITY_VERSION}-{token}"


def _normalize_selection(value: Any) -> str:
    raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if raw in {"starter", "starting", "starting_xi", "first_team"}:
        return "starting"
    if raw in {"sub", "bench", "substitute", "substitution"}:
        return "substitute"
    if raw in {"not_selected", "dropped", "reserve", "reserves", "out"}:
        return "not_selected"
    return "unspecified"


def _energy_band(fitness: int) -> str:
    if fitness >= 85:
        return "fresh"
    if fitness >= 65:
        return "normal"
    if fitness >= 45:
        return "tired"
    return "exhausted"


def _mood_band(morale: int) -> str:
    if morale >= 70:
        return "confident"
    if morale >= 40:
        return "neutral"
    return "subdued"


def _stress_band(stress: int) -> str:
    return "tense" if stress >= 70 else "calm"


def _expression(energy: str, mood: str, stress_band: str, injured: bool) -> str:
    # Explicit precedence makes presentation deterministic and easy to test.
    if injured:
        return "strained"
    if energy == "exhausted":
        return "exhausted"
    if stress_band == "tense":
        return "tense"
    if mood == "subdued":
        return "subdued"
    if mood == "confident":
        return "confident"
    return "neutral"


def _posture(energy: str, injured: bool) -> str:
    if injured:
        return "guarded"
    return {
        "fresh": "upright",
        "normal": "balanced",
        "tired": "lowered",
        "exhausted": "slumped",
    }[energy]


def build_player_visual(
    career: Any,
    *,
    selection_status: Any = None,
    context: str = "default",
) -> dict[str, Any]:
    """Build a versioned, deterministic visual model from career state.

    Permanent appearance depends only on the stable career id.
    Club kit depends only on the current club id.
    Dynamic presentation depends only on authoritative career/match state.
    """
    career_id = str(_read(career, "id", "unknown"))
    club_id = str(_read(career, "club_id", "unknown"))

    skin, skin_shadow = _choice(career_id, "skin_palette", SKIN_PALETTES)
    hair, hair_highlight = _choice(career_id, "hair_palette", HAIR_PALETTES)
    kit_primary, kit_secondary, kit_accent = _choice(
        club_id, "kit_palette", KIT_PALETTES
    )

    fitness = _bounded_int(_read(career, "fitness", 75), 75, 0, 100)
    morale = _bounded_int(_read(career, "morale", 50), 50, 0, 100)
    stress = _bounded_int(_read(career, "stress", 35), 35, 0, 100)
    injured_weeks = _bounded_int(_read(career, "injured_weeks", 0), 0, 0, 52)
    suspended_matches = _bounded_int(
        _read(career, "suspended_matches", 0), 0, 0, 50
    )
    overall = _bounded_int(_read(career, "overall", 50), 50, 1, 99)

    energy = _energy_band(fitness)
    mood = _mood_band(morale)
    stress_band = _stress_band(stress)
    injured = injured_weeks > 0
    selection = _normalize_selection(selection_status)
    safe_context = context if context in VALID_CONTEXTS else "default"

    name = str(_read(career, "player_name", "Player")).strip() or "Player"
    position = str(_read(career, "position", "UNK")).strip().upper() or "UNK"
    club_name = str(_read(career, "club_name", "Unattached")).strip() or "Unattached"

    return {
        "version": VISUAL_IDENTITY_VERSION,
        "identity_key": _identity_key(career_id),
        "name": name,
        "position": position,
        "overall": overall,
        "club_name": club_name,
        "appearance": {
            "skin": skin,
            "skin_shadow": skin_shadow,
            "hair": hair,
            "hair_highlight": hair_highlight,
            "hair_style": _choice(career_id, "hair_style", HAIR_STYLES),
            "face_shape": _choice(career_id, "face_shape", FACE_SHAPES),
            "eye_style": _choice(career_id, "eye_style", EYE_STYLES),
            "brow_style": _choice(career_id, "brow_style", BROW_STYLES),
            "nose_style": _choice(career_id, "nose_style", NOSE_STYLES),
            "build": _choice(career_id, "build", BUILD_STYLES),
            "facial_hair": _choice(
                career_id, "facial_hair", FACIAL_HAIR_STYLES
            ),
        },
        "kit": {
            "primary": kit_primary,
            "secondary": kit_secondary,
            "accent": kit_accent,
            "pattern": _choice(club_id, "kit_pattern", KIT_PATTERNS),
        },
        "state": {
            "fitness": fitness,
            "morale": morale,
            "stress": stress,
            "energy": energy,
            "mood": mood,
            "stress_band": stress_band,
            "selection": selection,
            "injury": "injured" if injured else "fit",
            "injured_weeks": injured_weeks,
            "suspended": suspended_matches > 0,
            "suspended_matches": suspended_matches,
        },
        "presentation": {
            "context": safe_context,
            "expression": _expression(energy, mood, stress_band, injured),
            "posture": _posture(energy, injured),
            "sweat_level": 2 if energy == "exhausted" else 1 if energy == "tired" else 0,
            "treatment": injured,
        },
        "a11y_label": f"{name}, {position}, {overall} overall, {club_name}",
    }

