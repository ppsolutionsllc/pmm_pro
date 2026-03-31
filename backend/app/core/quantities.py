from __future__ import annotations

import math


def round_up_quantity(value: float | int | None) -> int:
    if value is None:
        return 0
    numeric = float(value)
    if numeric <= 0:
        return 0
    return int(math.ceil(numeric - 1e-9))


def round_up_signed_quantity(value: float | int | None) -> int:
    if value is None:
        return 0
    numeric = float(value)
    if abs(numeric) < 1e-9:
        return 0
    if numeric > 0:
        return int(math.ceil(numeric - 1e-9))
    return -int(math.ceil(abs(numeric) - 1e-9))
