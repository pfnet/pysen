import copy
import dataclasses
import functools
import pathlib
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from pysen import process_utils
from pysen.command import check_command_installed
from pysen.dist_version import get_version
from pysen.error_lines import parse_error_lines
from pysen.exceptions import IncompatibleVersionError
from pysen.path import change_dir
from pysen.reporter import Reporter
from pysen.setting import SettingBase, to_dash_case

_SettingFileName = "setup.cfg"


def _contains(target: Sequence[str], item: str) -> bool:
    code_category = item[0].upper()

    for x in target:
        if len(x) == 1:
            if x.upper() == code_category:
                return True
        else:
            if x == item:
                return True

    return False


@dataclasses.dataclass
class Flake8Setting(SettingBase):
    max_line_length: int = 88
    select: Optional[List[str]] = None
    ignore: Optional[List[str]] = None
    enable_extensions: Optional[List[str]] = None
    max_complexity: Optional[int] = None

    _comments: List[str] = dataclasses.field(default_factory=list)

    @staticmethod
    def default() -> "Flake8Setting":
        return Flake8Setting(
            select=["B", "C", "E", "F", "W", "B950"],
        ).to_black_compatible()

    def to_black_compatible(self) -> "Flake8Setting":
        new = copy.deepcopy(self)
        if new.ignore is None:
            new.ignore = []

        if not _contains(new.ignore, "E203"):
            new.ignore.append("E203")
            new._comments.append("# E203: black treats : as a binary operator")

        if not _contains(new.ignore, "E231"):
            new.ignore.append("E231")
            new._comments.append("# E231: black doesn't put a space after ,")

        if not _contains(new.ignore, "E501"):
            new.ignore.append("E501")
            new._comments.append(
                "# E501: black may exceed the line-length to follow other style rules"
            )

        W503_or_504_enabled = _contains(new.ignore, "W503") or _contains(
            new.ignore, "W504"
        )
        if not W503_or_504_enabled:
            new.ignore.append("W503")
            new._comments.append(
                "# W503 or W504: either one needs to be disabled to select W error codes"
            )

        return new

    def export(self) -> Tuple[Sequence[str], Dict[str, Any]]:
        section_name = "flake8"
        entries = self.asdict(
            omit_none=True, naming_rule=to_dash_case, ignore_fields=["_comments"]
        )
        for c in self._comments:
            assert c.startswith("#") and c not in entries
            entries[c] = None

        return [section_name], entries


@functools.lru_cache(1)
def _check_flake8_version() -> None:
    version = get_version("flake8")
    if version.major != 3 or version.minor < 7:
        raise IncompatibleVersionError(
            "pysen only supports flake8 version >=3.7, <4. "
            f"version {version} is not supported."
        )


def run(
    reporter: Reporter,
    base_dir: pathlib.Path,
    setting_path: pathlib.Path,
    sources: Iterable[pathlib.Path],
) -> int:
    check_command_installed("flake8", "--version")
    _check_flake8_version()
    targets = [str(d) for d in sources]
    if len(targets) == 0:
        return 0

    cmd = ["flake8", "--config", str(setting_path)] + targets
    with change_dir(base_dir):
        ret, stdout, _ = process_utils.run(cmd, reporter)

    diagnostics = parse_error_lines(stdout, logger=reporter.logger)
    reporter.report_diagnostics(list(diagnostics))

    return ret
