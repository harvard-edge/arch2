import re

from ...contracts import ContractError


def transform(source, action):
    if action.name not in ("serial_mul1", "serial_mul2") or action.parameters:
        raise ContractError("Choose serial_mul1 or serial_mul2 without parameters")
    bits = 1 if action.name == "serial_mul1" else 2
    updated, count = re.subn(
        r"parameter integer MUL_BITS = \d+",
        f"parameter integer MUL_BITS = {bits}",
        source,
    )
    if count != 1:
        raise ContractError(
            "Core source must contain exactly one multiplier-width parameter"
        )
    return updated
