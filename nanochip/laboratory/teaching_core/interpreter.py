"""Independent scalar ISA interpreter; contains no neural-network operators."""
from dataclasses import dataclass
import struct
from .isa import Op, DATA_BASE, TABLE_BASE, decode, signed


@dataclass
class ExecutionResult:
    image: bytes
    logits: list
    argmax: list
    instructions_executed: int
    scratch: list
    external_reads: int
    external_writes: int
    observations: dict


def execute(compiled, image: bytes, *, max_instructions=100_000_000):
    """Execute only encoded instructions, with checked uninitialized scratch."""
    if len(compiled.program) % 16:
        raise ValueError("Truncated instruction stream")
    if compiled.manifest.get("token_count") is not None:
        if struct.unpack_from("<I", image, 19 * 4)[0] != compiled.token_count:
            raise ValueError("Image/program sequence length mismatch")
    instructions = [
        decode(int.from_bytes(compiled.program[i : i + 16], "little"))
        for i in range(0, len(compiled.program), 16)
    ]
    mem = bytearray(max(DATA_BASE + len(image), TABLE_BASE + len(compiled.tables)))
    mem[DATA_BASE : DATA_BASE + len(image)] = image
    mem[TABLE_BASE : TABLE_BASE + len(compiled.tables)] = compiled.tables
    regs = [0] * 16
    scratch = [None] * compiled.required_words
    pc = count = reads = writes = 0
    observations = {}
    observation_points = {}
    for point in compiled.manifest.get("observations", []):
        observation_points.setdefault(point["pc"], []).append(point)
    while True:
        if not 0 <= pc < len(instructions):
            raise RuntimeError(f"Invalid PC {pc}")
        if count >= max_instructions:
            raise RuntimeError("Instruction limit exceeded")
        for point in observation_points.get(pc, []):
            vals = [scratch[a] for a in point["words"]]
            if any(v is None for v in vals):
                raise RuntimeError("Uninitialized observed scratch")
            observations.setdefault(point["name"], []).append(vals)
        d = instructions[pc]
        op = d["op"]
        a = regs[d["ra"]]
        b = regs[d["rb"]]
        imm = d["imm"]
        pc += 1
        count += 1
        if op == Op.HALT:
            break
        if op == Op.LI:
            v = imm
        elif op == Op.ADD:
            v = a + b
        elif op == Op.SUB:
            v = a - b
        elif op == Op.MUL:
            v = a * b
        elif op == Op.ASR:
            v = a >> (b & 127)
        elif op == Op.SHL:
            v = a << (b & 127)
        elif op == Op.AND:
            v = a & b
        elif op == Op.OR:
            v = a | b
        elif op == Op.XOR:
            v = a ^ b
        elif op == Op.LT:
            v = int(a < b)
        elif op == Op.EQ:
            v = int(a == b)
        elif op == Op.JZ:
            if a == 0:
                pc = imm
            continue
        elif op == Op.JMP:
            pc = imm
            continue
        elif op in (Op.LDS, Op.STS):
            addr = a + imm
            if not 0 <= addr < len(scratch):
                raise RuntimeError(f"Scratch bounds {addr}")
            if op == Op.STS:
                scratch[addr] = signed(b, 32)
                continue
            if scratch[addr] is None:
                raise RuntimeError(f"Uninitialized scratch {addr} at PC {pc-1}")
            v = scratch[addr]
        elif op in (Op.LDX, Op.STX):
            addr = a + imm
            width = 4 if op == Op.STX else 1 << (d["flags"] & 3)
            if not (
                (DATA_BASE <= addr and addr + width <= DATA_BASE + len(image))
                or (
                    TABLE_BASE <= addr
                    and addr + width <= TABLE_BASE + len(compiled.tables)
                )
            ):
                raise RuntimeError(f"External bounds {addr}")
            if op == Op.STX:
                if addr % 4:
                    raise RuntimeError("Unaligned external store")
                mem[addr : addr + 4] = (b & 0xFFFFFFFF).to_bytes(4, "little")
                writes += 1
                continue
            v = int.from_bytes(
                mem[addr : addr + width], "little", signed=bool(d["flags"] & 4)
            )
            reads += 1
        elif op == Op.SAT32:
            v = max(-(1 << 31), min((1 << 31) - 1, a))
        else:
            raise RuntimeError(op)
        regs[d["rd"]] = signed(v)
    result = bytes(mem[DATA_BASE : DATA_BASE + len(image)])
    h = struct.unpack_from("<64I", result)
    logits = [
        list(struct.unpack_from(f"<{h[17]}i", result, h[25] + p * h[30]))
        for p in range(h[19])
    ]
    argmax = list(struct.unpack_from(f"<{h[19]}I", result, h[26]))
    return ExecutionResult(
        result, logits, argmax, count, scratch, reads, writes, observations
    )
