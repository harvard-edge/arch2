"""Student-editable XBUF mapping, matching frozen rtl/msh_mem.v.

Replace either function, run ``python3 -m nanochip.laboratory.teaching_target
check``, and explain a reported counterexample. This maps all input bit
patterns, including aliases; it does not declare aliased addresses legal.
"""


def word_address(address: int) -> int:
    """Map the wrapper's {buffer, word} input to its SRAM word address."""
    if type(address) is not int or not 0 <= address < (1 << 14):
        raise ValueError("XBUF address must be an unsigned 14-bit integer")
    return (((address >> 9) & 0xF) << 5) | (address & 0x1F)


def byte_strobes(lane_mask: int) -> int:
    """Expand four int32 lane enables into sixteen byte enables."""
    if type(lane_mask) is not int or not 0 <= lane_mask < (1 << 4):
        raise ValueError("XBUF lane mask must be an unsigned 4-bit integer")
    return sum(0xF << (lane * 4) for lane in range(4) if (lane_mask >> lane) & 1)
