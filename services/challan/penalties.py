"""Per-violation penalty amounts (INR) — Motor Vehicles Act indicative fines."""

VIOLATION_PENALTY_INR: dict[str, int] = {
    "helmet_non_compliance": 1_000,
    "triple_riding": 2_000,
    "wrong_side_driving": 3_000,
    "illegal_parking": 500,
    "seatbelt_non_compliance": 1_500,
    "stop_line_violation": 1_000,
    "red_light_violation": 5_000,
}


def penalty_for_violation(violation_type: str) -> int:
    return VIOLATION_PENALTY_INR.get(violation_type, 1_000)
