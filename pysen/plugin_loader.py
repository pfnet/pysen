import importlib
import pathlib
from types import ModuleType
from typing import Optional

from . import py_module
from .exceptions import InvalidPluginError
from .plugin import PluginBase
from .py_module import _parse_entry_point


def _load(module: ModuleType, func_name: str) -> PluginBase:
    entry_point = getattr(module, func_name, None)
    if entry_point is None or not callable(entry_point):
        raise InvalidPluginError(
            module.__file__, f"expected to have `{func_name}` method: {module.__file__}"
        )

    try:
        ret = entry_point()
    except Exception as e:
        raise RuntimeError(
            f"an error occured while loading {module.__file__}::{func_name}",
        ) from e

    if not isinstance(ret, PluginBase):
        raise InvalidPluginError(
            module.__file__, f"`{func_name}` must return an instance of PluginBase"
        )

    return ret


def load_from_file(path: pathlib.Path) -> PluginBase:
    module = py_module.load(path, "plugin")
    return _load(module, "plugin")


def load_from_module(entry_point: str) -> PluginBase:
    parsed = _parse_entry_point(entry_point)
    if parsed is None:
        raise ValueError(f"invalid entry_point: {entry_point}")

    module_name, func_name = parsed
    module = importlib.import_module(module_name)
    return _load(module, func_name)


def load_plugin(
    function: Optional[str] = None, script: Optional[pathlib.Path] = None
) -> PluginBase:
    if function is None and script is None:
        raise TypeError("must specify either function or script")

    if function is not None and script is not None:
        raise TypeError("only one of function or script must be speicifed")

    if function is not None:
        try:
            return load_from_module(function)
        except BaseException:
            if script is not None:
                pass  # fallback
            else:
                raise

    assert script is not None
    return load_from_file(script)
