"""Complete Kimi-derived teaching-core contract and reference fixtures.

The fixture path is not an RTL implementation or a physical acceptance claim.
"""

from .contract import contract
from .fixtures import build_fixture
from .backend import make_task, TeachingCoreMaterializer, TeachingCoreBackend

__all__ = ["contract", "build_fixture", "make_task", "TeachingCoreMaterializer", "TeachingCoreBackend"]
