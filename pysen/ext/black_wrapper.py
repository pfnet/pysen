import dataclasses
import functools
import pathlib
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pysen import process_utils
from pysen.command import check_command_installed
from pysen.dist_version import get_version
from pysen.error_lines import parse_error_diffs
from pysen.exceptions import IncompatibleVersionError
from pysen.path import change_dir
from pysen.py_version import PythonVersion, VersionRepresentation
from pysen.reporter import Reporter
from pysen.setting import SettingBase, to_dash_case


@dataclasses.dataclass
class BlackSetting(SettingBase):
    line_length: int = 88
    target_version: List[PythonVersion] = dataclasses.field(default_factory=list)

    @staticmethod
    def default(
        # NOTE(igarashi) safe to use as an argument since it is immutable
        py_version: Optional[PythonVersion] = None,
    ) -> "BlackSetting":
        py_version = py_version or PythonVersion(3, 7)
        return BlackSetting(target_version=[py_version])

    def export(self) -> Tuple[List[str], Dict[str, Any]]:
        section_name = ["tool", "black"]

        # TODO(igarashi): refactor these flaky code
        # `dataclass.asdict()` converts `PythonVersion` object into an undesired dict like
        # `{"major": ...}` as it is defined by a dataclass.
        # `SettingBase.asdict` takes `type_hooks` argument, but it doesn't work as expected
        # because the hook is called after `dataclass.asdict()` is called.
        # In order to dump PythonVersion objects into a desired representation,
        # the following code ignores the field when calling `asdict` and replaces it
        # with the desired dump after we call `asdict()`
        entries = self.asdict(
            ignore_fields=["target_version"], naming_rule=to_dash_case
        )
        entries["target-version"] = []
        for v in self.target_version:
            entries["target-version"].append(v.short_representation)
        return section_name, entries


def _parse_file_path(file_path: str) -> pathlib.Path:
    return pathlib.Path(file_path.split(" ")[0])


@functools.lru_cache(1)
def _check_black_version() -> None:
    version = get_version("black")
    compatible_versions = [
        VersionRepresentation(19, 10),
        VersionRepresentation(20, 8),
    ]

    if all(not v.is_compatible(version) for v in compatible_versions):
        raise IncompatibleVersionError(
            "pysen only supports black versions: "
            f"{{{', '.join(v.version for v in compatible_versions)}}}. "
            f"version {version} is not supported."
        )


def run(
    reporter: Reporter,
    base_dir: pathlib.Path,
    setting_path: pathlib.Path,
    sources: Iterable[pathlib.Path],
    inplace_edit: bool,
) -> int:
    check_command_installed("black", "--version")
    _check_black_version()

    targets = [str(d) for d in sources]
    if len(targets) == 0:
        return 0

    cmd = (
        ["black", "--config", str(setting_path)]
        + (["--diff", "--check"] if not inplace_edit else [])
        + targets
    )
    with change_dir(base_dir):
        ret, stdout, _ = process_utils.run(cmd, reporter)

    diagnostics = parse_error_diffs(stdout, _parse_file_path, logger=reporter.logger)
    reporter.report_diagnostics(list(diagnostics))

    return ret
