from __future__ import annotations

import math

from .engine import POSITION_WEIGHTS, calculate_overall


ATTRIBUTES = (
    "pace",
    "shooting",
    "passing",
    "dribbling",
    "defending",
    "physical",
)


def _base_upgrade_cost(attribute_value: int) -> int:
    value = max(0, min(99, int(attribute_value)))
    if value < 60:
        return 60
    if value < 70:
        return 75
    if value < 80:
        return 105
    if value < 85:
        return 145
    if value < 90:
        return 200
    return 280


def _potential_cost_multiplier(overall: int, potential: int) -> float:
    gap = int(potential) - int(overall)
    if gap >= 25:
        return 0.80
    if gap >= 15:
        return 0.90
    if gap >= 8:
        return 1.00
    if gap >= 3:
        return 1.20
    return 1.50


def upgrade_cost(attribute_value: int, overall: int, potential: int) -> int:
    return max(1, round(_base_upgrade_cost(attribute_value) * _potential_cost_multiplier(overall, potential)))


def largest_remainder_scale(values: dict[str, float], target_total: int) -> dict[str, int]:
    if not values:
        return {}
    cap = max(0, int(target_total))
    clean = {key: max(0.0, float(value)) for key, value in values.items()}
    raw_total = sum(clean.values())
    if raw_total <= 0 or cap <= 0:
        return {key: 0 for key in clean}

    desired_total = min(cap, round(raw_total))
    if raw_total > cap:
        factor = cap / raw_total
        scaled = {key: value * factor for key, value in clean.items()}
        desired_total = cap
    else:
        scaled = clean

    floors = {key: math.floor(value) for key, value in scaled.items()}
    remainder = desired_total - sum(floors.values())
    rank = {name: index for index, name in enumerate(ATTRIBUTES)}
    ordered = sorted(
        scaled,
        # Ignore binary-float noise so mathematical ties use attribute order.
        key=lambda key: (-round(scaled[key] - floors[key], 12), rank.get(key, len(ATTRIBUTES)), key),
    )
    result = dict(floors)
    for key in ordered[:max(0, remainder)]:
        result[key] += 1
    return result


def _normalise(values: dict[str, int], default: int) -> dict[str, int]:
    return {name: max(0, int(values.get(name, default))) for name in ATTRIBUTES}


def apply_attribute_xp(*, attributes: dict[str, int], meters: dict[str, int], gains: dict[str, int], position: str, potential: int) -> dict:
    current_attributes = _normalise(attributes, 50)
    current_meters = _normalise(meters, 0)
    for name in ATTRIBUTES:
        current_meters[name] += max(0, int(gains.get(name, 0)))

    upgrades = []
    potential = max(1, min(99, int(potential)))

    for name in ATTRIBUTES:
        while current_attributes[name] < 99:
            overall = calculate_overall(current_attributes, position, potential)
            if overall >= potential:
                return {
                    "attributes": current_attributes,
                    "meters": current_meters,
                    "overall": overall,
                    "upgrades": upgrades,
                }
            cost = upgrade_cost(current_attributes[name], overall, potential)
            if current_meters[name] < cost:
                break
            before = current_attributes[name]
            current_meters[name] -= cost
            current_attributes[name] += 1
            upgrades.append({"attribute": name, "from": before, "to": current_attributes[name]})

    return {
        "attributes": current_attributes,
        "meters": current_meters,
        "overall": calculate_overall(current_attributes, position, potential),
        "upgrades": upgrades,
    }


def rating_multiplier(rating: float) -> float:
    if rating < 6.5:
        return 0.90
    if rating < 7.5:
        return 1.00
    if rating < 8.5:
        return 1.10
    return 1.20


def match_development_xp(performance: dict) -> dict[str, int]:
    """Derive XP without mutating the authoritative performance snapshot.

    The caller must attach actual minutes: the simulator's return value does
    not include them. Missing/non-positive minutes never earn match XP.
    """
    minutes = max(0, int(performance.get("minutes", 0)))
    if minutes == 0:
        return dict.fromkeys(ATTRIBUTES, 0)

    metrics = performance.get("metrics", {})

    def metric(name: str) -> float:
        return max(0.0, float(metrics.get(name, 0)))

    goals = max(0, int(performance.get("goals", 0)))
    assists = max(0, int(performance.get("assists", 0)))
    completed_dribbles = metric("dribbles_completed")
    duels_won = metric("duels_won")
    progressive = metric("progressive_actions")

    passing = metric("passes_completed") * 0.20 + metric("key_passes") * 3 + assists * 8
    if metric("passes_attempted") >= 20:
        if metric("pass_accuracy") >= 85:
            passing += 5
        if metric("pass_accuracy") >= 92:
            passing += 3

    shooting = metric("shots") + metric("shots_on_target") * 2 + goals * 10
    if metric("shots") >= 2 and metric("shot_accuracy") >= 50:
        shooting += 3

    dribbling = completed_dribbles * 2.5 + progressive * 0.35
    if metric("dribbles_attempted") >= 3 and metric("dribble_success") >= 60:
        dribbling += 4

    defending = metric("tackles_won") * 3 + duels_won
    if metric("tackles_attempted") >= 2 and metric("tackle_success") >= 70:
        defending += 4

    physical = minutes // 10 + duels_won * 0.6 + (2 if minutes >= 90 else 0)
    pace = progressive + completed_dribbles * 0.5 + (2 if minutes >= 60 else 0)
    capped = {
        "pace": min(12, pace),
        "shooting": min(24, shooting),
        "passing": min(28, passing),
        "dribbling": min(20, dribbling),
        "defending": min(22, defending),
        "physical": min(15, physical),
    }
    multiplier = rating_multiplier(float(performance.get("rating", 6.5)))
    # Approved spec: round each multiplied category before the global cap.
    multiplied = {name: round(value * multiplier) for name, value in capped.items()}
    return largest_remainder_scale(multiplied, 75)


TRAINING_SUPPORT = {
    "pace": ("dribbling", "physical"),
    "shooting": ("dribbling", "physical"),
    "passing": ("dribbling", "physical"),
    "dribbling": ("pace", "passing"),
    "defending": ("physical", "passing"),
    "physical": ("pace", "defending"),
}


def training_development_xp(*, focus: str, position: str, season_phase: str,
                            minutes: int, unavailable_injured: bool) -> dict[str, int]:
    """Allocate one week's training; changing focus never calls persistence."""
    if focus == "recovery" or unavailable_injured:
        return dict.fromkeys(ATTRIBUTES, 0)

    load = 0.70 if minutes >= 60 else 0.80 if minutes >= 30 else 0.90 if minutes > 0 else 1.00
    multiplier = load * (1.25 if season_phase == "preseason" else 1.00)
    target = round(30 * multiplier)
    if focus == "balanced":
        # Start from the rounded budget: the allocator does not pad to its cap.
        weights = POSITION_WEIGHTS[position]
        gains = {name: target * weights[name] for name in ATTRIBUTES}
    else:
        support_a, support_b = TRAINING_SUPPORT[focus]
        gains = dict.fromkeys(ATTRIBUTES, 0.0)
        gains[focus] = 20 * multiplier
        gains[support_a] = 5 * multiplier
        gains[support_b] = 5 * multiplier
    return largest_remainder_scale(gains, target)
