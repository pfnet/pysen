import copy
import dataclasses
import enum
import functools
import pathlib
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from pysen import process_utils
from pysen.command import check_command_installed
from pysen.dist_version import get_version
from pysen.error_lines import parse_error_diffs
from pysen.exceptions import IncompatibleVersionError, UnexpectedErrorFormat
from pysen.path import change_dir
from pysen.py_version import VersionRepresentation
from pysen.reporter import Reporter
from pysen.setting import SettingBase

_SettingFileName = "pyproject.toml"


class IsortSectionName(enum.Enum):
    FUTURE = "FUTURE"
    STDLIB = "STDLIB"
    THIRDPARTY = "THIRDPARTY"
    FIRSTPARTY = "FIRSTPARTY"
    LOCALFOLDER = "LOCALFOLDER"


@functools.lru_cache(1)
def _get_isort_version() -> VersionRepresentation:
    version = get_version("isort")
    if version.major not in [4, 5]:
        raise IncompatibleVersionError(
            "pysen only supports isort versions 4 and 5. "
            f"version {version} is not supported."
        )

    return version


def _check_version_compatibility(
    ensure_newline_before_comments: Optional[bool],
    version: VersionRepresentation,
) -> None:
    if version.major == 4 and ensure_newline_before_comments is not None:
        raise IncompatibleVersionError(
            "isort option `ensure_newline_before_comments`"
            f"is not supported in your isort version {version}"
        )


@dataclasses.dataclass
class IsortSetting(SettingBase):
    force_grid_wrap: int = 0
    force_single_line: bool = False
    include_trailing_comma: bool = True
    known_first_party: Optional[Set[str]] = None
    known_third_party: Optional[Set[str]] = None
    line_length: int = 88
    multi_line_output: int = 3
    default_section: Optional[IsortSectionName] = None
    sections: Optional[List[IsortSectionName]] = None
    use_parentheses: bool = True
    ensure_newline_before_comments: Optional[bool] = None

    @staticmethod
    def default() -> "IsortSetting":
        return IsortSetting()

    def to_black_compatible(self) -> "IsortSetting":
        # NOTE(igarashi)
        # multi_line_output: black uses 3 (Vertical Hanging Indent)
        # include_trailing_comma: black appends trailing comma
        # force_grid_wrap: the property means isort grid-wrap the statement regardless
        #                  of line length if the number of `from` imports is greater than
        #                  the property. black doesn't grid wrap the statemenet if it
        #                  doesn't exceed the line length.
        # use_parentheses: use parenthesis for line continuation instead of `\`
        new = copy.deepcopy(self)

        new.multi_line_output = 3
        new.include_trailing_comma = True
        new.force_grid_wrap = 0
        new.use_parentheses = True

        # See issue #277
        isort_version = _get_isort_version().major
        if isort_version >= 5:
            new.ensure_newline_before_comments = True
        return new

    def export(self) -> Tuple[List[str], Dict[str, Any]]:
        section_name = ["tool", "isort"]

        _check_version_compatibility(
            self.ensure_newline_before_comments,
            _get_isort_version(),
        )
        entries = self.asdict(
            omit_none=True, type_hooks={IsortSectionName: lambda x: x.value}
        )
        return section_name, entries


def _parse_file_path(file_path: str) -> pathlib.Path:
    ret = file_path.split(" ")[0]
    before_suffix = ":before"
    after_suffix = ":after"
    if ret.endswith(before_suffix):
        return pathlib.Path(ret.rsplit(before_suffix, 1)[0])
    elif ret.endswith(after_suffix):
        return pathlib.Path(ret.rsplit(after_suffix, 1)[0])
    else:
        raise UnexpectedErrorFormat(file_path)


def run(
    reporter: Reporter,
    base_dir: pathlib.Path,
    setting_path: pathlib.Path,
    sources: Iterable[pathlib.Path],
    inplace_edit: bool,
) -> int:
    check_command_installed("isort", "--version")
    version = _get_isort_version()

    targets = [str(d) for d in sources]
    if len(targets) == 0:
        return 0

    cmd = ["isort", "--settings-path", str(setting_path)]
    if version.major == 4:
        cmd.append("--recursive")
    if not inplace_edit:
        cmd += ["--diff", "--check-only"]
    cmd += targets

    with change_dir(base_dir):
        ret, stdout, _ = process_utils.run(cmd, reporter)

    diagnostics = parse_error_diffs(stdout, _parse_file_path, logger=reporter.logger)
    reporter.report_diagnostics(list(diagnostics))

    return ret
