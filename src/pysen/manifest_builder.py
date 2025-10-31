import pathlib
from typing import Optional, Sequence

from . import py_module
from .component import ComponentBase
from .exceptions import InvalidManifestBuilderError
from .manifest import Manifest, ManifestBase


def _build_external(
    path: pathlib.Path,
    components: Sequence[ComponentBase],
    src_path: Optional[pathlib.Path],
) -> ManifestBase:
    module = py_module.load(path, "builder")
    entry_point = getattr(module, "build", None)
    if entry_point is None or not callable(entry_point):
        raise InvalidManifestBuilderError(
            path, "external builder must have `build` method"
        )

    ret = entry_point(components, src_path)
    if not isinstance(ret, ManifestBase):
        raise InvalidManifestBuilderError(
            path, "`build` must return an instance of ManifestBase"
        )

    return ret


def _build(
    components: Sequence[ComponentBase], src_path: Optional[pathlib.Path]
) -> ManifestBase:
    return Manifest(components)


def build(
    components: Sequence[ComponentBase],
    src_path: Optional[pathlib.Path] = None,
    external_builder: Optional[pathlib.Path] = None,
) -> ManifestBase:
    if external_builder is not None:
        return _build_external(external_builder, components, src_path)

    return _build(components, src_path)
