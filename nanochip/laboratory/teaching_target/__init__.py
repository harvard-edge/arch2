"""Source-derived core inventory and a bounded memory-interface exercise."""

from .inventory import derive_target, validate_target
from .exercise import check_mapping, run_memory_check

__all__ = ["derive_target", "validate_target", "check_mapping", "run_memory_check"]
