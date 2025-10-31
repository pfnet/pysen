import importlib.machinery
import itertools
import pathlib
import re
import sys
import types
from types import ModuleType
from typing import Optional, Tuple

_module_counter = itertools.count()


ID_REGEX = r"[_A-Za-z][_a-zA-Z0-9]*"
DOTTED_ID_REGEX = rf"{ID_REGEX}(\.{ID_REGEX})*"
ENTRY_POINT_REGEX = rf"^(?P<module>{DOTTED_ID_REGEX})::(?P<func>{ID_REGEX})$"

entry_point = re.compile(ENTRY_POINT_REGEX)


def _parse_entry_point(expr: str) -> Optional[Tuple[str, str]]:
    matches = list(entry_point.finditer(expr))
    if len(matches) != 1:
        return None

    match = matches[0]
    module = match.group("module")
    func = match.group("func")
    assert module is not None
    assert func is not None
    return module, func


def load(path: pathlib.Path, module_name_prefix: str) -> ModuleType:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)

    # NOTE(igarashi): add unique number to module_name to avoid module name conflict
    # NOTE(igarashi): since next(itertools.count) doesn't release GIL, it is an atomic operation
    counter = next(_module_counter)
    module_name = f"pysen._modules.{module_name_prefix}_{counter}"

    loader = importlib.machinery.SourceFileLoader(module_name, str(path))
    module = types.ModuleType(loader.name)
    # NOTE(igarashi): typing raises an error if the module is not included in sys.modules.
    # To allow loaded modules to use dacite, register them to `sys.modules`.
    sys.modules[module_name] = module

    module.__file__ = str(path)
    loader.exec_module(module)

    return module
