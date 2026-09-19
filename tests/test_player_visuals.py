from copy import deepcopy

import pytest


BASE = {
    "id": 17,
    "player_name": "Test Player",
    "position": "CM",
    "overall": 72,
    "club_id": 4,
    "club_name": "Test United",
    "fitness": 91,
    "morale": 78,
    "stress": 22,
    "injured_weeks": 0,
    "suspended_matches": 0,
}


def build(career=None, **kwargs):
    from app.player_visuals import build_player_visual
    return build_player_visual(BASE if career is None else career, **kwargs)


def test_same_career_produces_identical_visual_identity():
    assert build() == build()


def test_dynamic_state_does_not_change_permanent_appearance():
    tired = dict(BASE, fitness=38, morale=24, stress=91, injured_weeks=3)
    assert build(BASE)["identity_key"] == build(tired)["identity_key"]
    assert build(BASE)["appearance"] == build(tired)["appearance"]


def test_transfer_changes_kit_but_not_player_identity():
    transferred = dict(BASE, club_id=9, club_name="New Club")
    before = build(BASE)
    after = build(transferred)

    assert before["appearance"] == after["appearance"]
    assert before["identity_key"] == after["identity_key"]
    assert before["kit"] != after["kit"]


@pytest.mark.parametrize(
    ("fitness", "expected"),
    [(100, "fresh"), (85, "fresh"), (84, "normal"), (65, "normal"),
     (64, "tired"), (45, "tired"), (44, "exhausted"), (0, "exhausted")],
)
def test_fitness_boundaries_are_explicit(fitness, expected):
    assert build(dict(BASE, fitness=fitness))["state"]["energy"] == expected


@pytest.mark.parametrize(
    ("morale", "expected"),
    [(100, "confident"), (70, "confident"), (69, "neutral"),
     (40, "neutral"), (39, "subdued"), (0, "subdued")],
)
def test_morale_boundaries_are_explicit(morale, expected):
    assert build(dict(BASE, morale=morale))["state"]["mood"] == expected


def test_injury_is_derived_only_from_authoritative_injured_weeks():
    fit = build(dict(BASE, injured_weeks=0))
    hurt = build(dict(BASE, injured_weeks=2))

    assert fit["state"]["injury"] == "fit"
    assert fit["presentation"]["treatment"] is False
    assert hurt["state"]["injury"] == "injured"
    assert hurt["state"]["injured_weeks"] == 2
    assert hurt["presentation"]["treatment"] is True
    assert hurt["presentation"]["expression"] == "strained"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("starter", "starting"),
        ("starting_xi", "starting"),
        ("bench", "substitute"),
        ("sub", "substitute"),
        ("not_selected", "not_selected"),
        ("dropped", "not_selected"),
        (None, "unspecified"),
        ("unexpected-value", "unspecified"),
    ],
)
def test_selection_status_is_normalized_to_safe_enum(raw, expected):
    assert build(selection_status=raw)["state"]["selection"] == expected


def test_unknown_context_and_bad_numbers_degrade_safely():
    career = dict(
        BASE,
        fitness="bad",
        morale=None,
        stress=500,
        overall=-20,
        injured_weeks=-8,
    )
    visual = build(career, context="../../unsafe")

    assert visual["presentation"]["context"] == "default"
    assert visual["state"]["fitness"] == 75
    assert visual["state"]["morale"] == 50
    assert visual["state"]["stress"] == 100
    assert visual["overall"] == 1
    assert visual["state"]["injured_weeks"] == 0


def test_input_mapping_is_not_mutated():
    career = deepcopy(BASE)
    original = deepcopy(career)

    build(career, selection_status="starter", context="match")

    assert career == original


def test_name_and_nationality_do_not_define_physical_identity():
    changed_profile_text = dict(
        BASE,
        player_name="Renamed Player",
        nationality="Different",
    )
    before = build(BASE)
    after = build(changed_profile_text)

    assert before["identity_key"] == after["identity_key"]
    assert before["appearance"] == after["appearance"]


def test_output_is_constrained_to_declared_trait_sets():
    from app import player_visuals as pv

    visual = build()

    assert (visual["appearance"]["skin"], visual["appearance"]["skin_shadow"]) in pv.SKIN_PALETTES
    assert (visual["appearance"]["hair"], visual["appearance"]["hair_highlight"]) in pv.HAIR_PALETTES
    assert visual["appearance"]["hair_style"] in pv.HAIR_STYLES
    assert visual["appearance"]["face_shape"] in pv.FACE_SHAPES
    assert visual["appearance"]["eye_style"] in pv.EYE_STYLES
    assert visual["appearance"]["brow_style"] in pv.BROW_STYLES
    assert visual["appearance"]["nose_style"] in pv.NOSE_STYLES
    assert visual["appearance"]["build"] in pv.BUILD_STYLES
    assert visual["appearance"]["facial_hair"] in pv.FACIAL_HAIR_STYLES
    assert visual["kit"]["pattern"] in pv.KIT_PATTERNS
    assert visual["state"]["selection"] in pv.VALID_SELECTIONS
    assert visual["identity_key"].startswith("v1-")

