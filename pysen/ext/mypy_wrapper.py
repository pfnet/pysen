import dataclasses
import enum
import functools
import pathlib
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pysen import process_utils
from pysen.command import check_command_installed
from pysen.dist_version import get_version
from pysen.error_lines import parse_error_lines
from pysen.exceptions import IncompatibleVersionError
from pysen.path import PathLikeType, change_dir, get_relative_path, resolve_path
from pysen.py_version import PythonVersion
from pysen.reporter import Reporter
from pysen.setting import SettingBase

_IgnoreFields: List[str] = ["_pysen_convert_abspath"]


class MypyFollowImports(enum.Enum):
    NORMAL = "normal"
    SILENT = "silent"
    SKIP = "skip"
    ERROR = "error"


@dataclasses.dataclass
class MypyPlugin:
    script: Optional[pathlib.Path] = None
    function: Optional[str] = None

    def __post_init__(self) -> None:
        if self.script is None and self.function is None:
            raise ValueError("either script or function must be specified")

        if self.script is not None and self.function is not None:
            raise ValueError("cannot specify both script and function")

    def as_config(self, relative_from: Optional[pathlib.Path] = None) -> str:
        if self.function is not None:
            return self.function

        assert self.script is not None
        if relative_from is not None:
            return get_relative_path(self.script, relative_from)
        else:
            return str(self.script)


@dataclasses.dataclass
class MypySetting(SettingBase):
    python_version: Optional[PythonVersion] = None

    check_untyped_defs: Optional[bool] = None
    disallow_any_decorated: Optional[bool] = None
    disallow_any_generics: Optional[bool] = None
    disallow_any_unimported: Optional[bool] = None
    disallow_incomplete_defs: Optional[bool] = None
    disallow_subclassing_any: Optional[bool] = None
    disallow_untyped_calls: Optional[bool] = None
    disallow_untyped_decorators: Optional[bool] = None
    disallow_untyped_defs: Optional[bool] = None
    follow_imports: Optional[MypyFollowImports] = None
    ignore_errors: Optional[bool] = None
    ignore_missing_imports: Optional[bool] = None
    mypy_path: Optional[List[PathLikeType]] = None
    no_implicit_optional: Optional[bool] = None
    pretty: Optional[bool] = None
    show_error_codes: Optional[bool] = None
    strict_equality: Optional[bool] = None
    strict_optional: Optional[bool] = None
    warn_redundant_casts: Optional[bool] = None
    warn_return_any: Optional[bool] = None
    warn_unreachable: Optional[bool] = None
    warn_unused_configs: Optional[bool] = None
    warn_unused_ignores: Optional[bool] = None
    plugins: Optional[List[MypyPlugin]] = None

    # configuration for export settings
    _pysen_convert_abspath: bool = False

    @staticmethod
    def very_strict(**kwargs: Any) -> "MypySetting":
        updates = {
            "check_untyped_defs": True,
            "disallow_any_decorated": True,
            "disallow_any_generics": True,
            "disallow_any_unimported": True,
            "disallow_incomplete_defs": True,
            "disallow_subclassing_any": True,
            "disallow_untyped_calls": True,
            "disallow_untyped_decorators": True,
            "disallow_untyped_defs": True,
            "ignore_errors": False,
            "ignore_missing_imports": False,
            "no_implicit_optional": True,
            "show_error_codes": True,
            "strict_equality": True,
            "strict_optional": True,
            "warn_redundant_casts": True,
            "warn_return_any": True,
            "warn_unreachable": True,
            "warn_unused_configs": True,
            "warn_unused_ignores": True,
        }
        updates.update(kwargs)
        return MypySetting(**updates)  # type: ignore

    @staticmethod
    def strict(**kwargs: Any) -> "MypySetting":
        updates = {
            "disallow_any_decorated": False,
            "disallow_any_unimported": False,
            "disallow_untyped_decorators": False,
            "ignore_missing_imports": True,
        }
        updates.update(kwargs)
        setting = MypySetting.very_strict(**updates)
        return setting

    @staticmethod
    def entry(**kwargs: Any) -> "MypySetting":
        updates = {
            "disallow_untyped_calls": False,
            "disallow_untyped_defs": False,
            "warn_return_any": False,
        }
        updates.update(kwargs)
        setting = MypySetting.strict(**updates)
        return setting

    def export(
        self, base_dir: pathlib.Path, target_module: Optional[str] = None
    ) -> Tuple[Sequence[str], Dict[str, Any]]:
        section_name = "mypy"
        if target_module is not None:
            section_name += f"-{target_module}"

        # TODO(igarashi): refactor these flaky code, see: black.py
        entries = self.asdict(
            _IgnoreFields
            + ["python_version", "mypy_path", "plugins", "follow_imports"],
            omit_none=True,
        )
        if self.python_version is not None:
            entries["python_version"] = self.python_version.version

        if self.mypy_path is not None:
            mypy_path: List[str] = []
            for p in self.mypy_path:
                path: str
                if self._pysen_convert_abspath:
                    path = get_relative_path(p, base_dir)
                else:
                    path = str(p)

                mypy_path.append(path)

            entries["mypy_path"] = mypy_path

        if self.plugins is not None:
            relative_from: Optional[pathlib.Path] = None
            if self._pysen_convert_abspath:
                relative_from = base_dir

            entries["plugins"] = [p.as_config(relative_from) for p in self.plugins]

        if self.follow_imports is not None:
            entries["follow_imports"] = self.follow_imports.value

        return [section_name], entries


@dataclasses.dataclass
class MypyTarget:
    paths: List[pathlib.Path]


@functools.lru_cache(1)
def _check_mypy_version() -> None:
    version = get_version("mypy")
    if version.major != 0 or version.minor < 770:
        raise IncompatibleVersionError(
            f"pysen only supports mypy version >=0.770, <1. "
            f"version {version} is not supported."
        )


def run(
    reporter: Reporter,
    base_dir: pathlib.Path,
    setting_path: pathlib.Path,
    target: MypyTarget,
    require_diagnostics: bool,
) -> int:
    check_command_installed("mypy", "--version")
    _check_mypy_version()

    target_paths = [str(resolve_path(base_dir, x)) for x in target.paths]
    if len(target_paths) == 0:
        return 0

    extra_options: List[str] = ["--show-absolute-path"]
    if require_diagnostics:
        extra_options += [
            "--no-color-output",
            "--show-column-numbers",
            "--no-error-summary",
        ]
    else:
        extra_options += [
            "--pretty",
        ]

    cmd = ["mypy"] + extra_options + ["--config-file", str(setting_path)] + target_paths
    with change_dir(base_dir):
        ret, stdout, _ = process_utils.run(cmd, reporter)

    if require_diagnostics:
        diagnostics = parse_error_lines(stdout, logger=reporter.logger)
        reporter.report_diagnostics(list(diagnostics))

    return ret
