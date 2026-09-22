from __future__ import annotations

import math

from .engine import calculate_overall


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
        key=lambda key: (-(scaled[key] - floors[key]), rank.get(key, len(ATTRIBUTES)), key),
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
