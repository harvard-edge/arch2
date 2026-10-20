"""Instructor mapping, independently expressed as ordered bit selections.

Source: msh_xbuf in frozen kpu/rtl/msh_mem.v, waddr/raddr concatenations
and w_wstrb replication. SRAM updates read the old word before writing.
"""


def word_address(address: int) -> int:
    if type(address) is not int or not 0 <= address < (1 << 14):
        raise ValueError("XBUF address must be an unsigned 14-bit integer")
    source_bits = (0, 1, 2, 3, 4, 9, 10, 11, 12)
    return sum(((address >> source) & 1) << dest for dest, source in enumerate(source_bits))


def byte_strobes(lane_mask: int) -> int:
    if type(lane_mask) is not int or not 0 <= lane_mask < (1 << 4):
        raise ValueError("XBUF lane mask must be an unsigned 4-bit integer")
    return sum(((lane_mask >> (byte // 4)) & 1) << byte for byte in range(16))


def masked_write(old: int, data: int, strobes: int, width: int) -> int:
    result = old
    for byte in range(width // 8):
        if (strobes >> byte) & 1:
            mask = 0xFF << (byte * 8)
            result = (result & ~mask) | (data & mask)
    return result
