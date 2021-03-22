import pathlib
from typing import Optional, Sequence

from pysen import ComponentBase


def build(components: Sequence[ComponentBase], src_path: Optional[pathlib.Path]) -> int:
    return 42
