"""Shared encoding for the teaching core's complete scalar microarchitecture."""

from enum import IntEnum

DATA_BASE = 1 << 20
TABLE_BASE = 1 << 22
SCRATCH_WORDS = 1024
REGISTER_COUNT = 16
WORD_BITS = 128
INSTRUCTION_BYTES = 16


class Op(IntEnum):
    HALT = 0
    LI = 1
    ADD = 2
    SUB = 3
    MUL = 4
    ASR = 5
    SHL = 6
    AND = 7
    OR = 8
    XOR = 9
    LT = 10
    EQ = 11
    JZ = 12
    JMP = 13
    LDS = 14
    STS = 15
    LDX = 16
    STX = 17
    SAT32 = 18


def encode(op: int | Op, rd: int = 0, ra: int = 0, rb: int = 0,
           imm: int = 0, flags: int = 0) -> int:
    op = Op(op)
    if any(type(r) is not int or not 0 <= r < REGISTER_COUNT for r in (rd, ra, rb)):
        raise ValueError("Register indices must be in range")
    if type(flags) is not int or not 0 <= flags < 16:
        raise ValueError("Flags must fit four bits")
    if type(imm) is not int or not -(1 << 63) <= imm < (1 << 63):
        raise ValueError("Immediate must be a signed64 integer")
    return int(op) | rd << 8 | ra << 12 | rb << 16 | flags << 20 | (imm & ((1 << 64) - 1)) << 32


def decode(word: int) -> dict:
    if type(word) is not int or not 0 <= word < (1 << WORD_BITS):
        raise ValueError("Instruction must be an unsigned128 integer")
    if word >> 96 or (word >> 24) & 0xFF:
        raise ValueError("Reserved instruction bits must be zero")
    immediate = (word >> 32) & ((1 << 64) - 1)
    if immediate & (1 << 63):
        immediate -= 1 << 64
    return {"op": Op(word & 0xFF), "rd": (word >> 8) & 15,
            "ra": (word >> 12) & 15, "rb": (word >> 16) & 15,
            "flags": (word >> 20) & 15, "imm": immediate}


def signed(value: int, width: int = WORD_BITS) -> int:
    value &= (1 << width) - 1
    return value - (1 << width) if value & (1 << (width - 1)) else value


def program_bytes(instructions) -> bytes:
    return b"".join(int(i).to_bytes(INSTRUCTION_BYTES, "little") for i in instructions)
