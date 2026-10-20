"""Student-owned RTL transformation, executed through the shared harness."""


def transform(source: str, action: str) -> str:
    """Return complete RTL for the selected action without editing source files.

    retain_indexed_read must return the unchanged source. stream_quantized_row
    must consume qrow_v[3:0] and shift right four bits on each S_WR cycle.
    Keep intake, fixed-point arithmetic, packing, and protocol behavior intact.
    Inspect the complete diff, then use the unchanged checkers to evaluate it.
    """
    raise NotImplementedError("Implement the design transformation in exercises/student_design.py")
