import dataclasses
import pathlib


@dataclasses.dataclass(frozen=True)
class PathContext:
    base_dir: pathlib.Path
    settings_dir: pathlib.Path


@dataclasses.dataclass(frozen=True)
class RunOptions:
    require_diagnostics: bool = True
    no_parallel: bool = False
