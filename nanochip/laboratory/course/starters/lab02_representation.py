"""Lab 2: preserve packed int4 weight order across software and RTL."""


def pack_int4(values):
    """Pack low then high nibbles into bytes."""
    raise NotImplementedError("Implement pack_int4")


def unpack_int4(packed):
    """Return each byte as its low nibble followed by its high nibble."""
    raise NotImplementedError("Implement unpack_int4")
