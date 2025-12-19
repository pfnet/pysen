import copy
import dataclasses
import enum
import functools
import pathlib
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from pysen import process_utils
from pysen.error_lines import parse_error_diffs
from pysen.path import change_dir
from pysen.reporter import Reporter


def _run_command_and_report(
    command: List[str], reporter: Reporter, base_dir: pathlib.Path
) -> int:
    def _parse_file_path(file_path: str) -> pathlib.Path:
        return base_dir / pathlib.Path(file_path.split(" ")[0])

    with change_dir(base_dir):
        ret, stdout, _ = process_utils.run(
            process_utils.add_python_executable(*command), reporter
        )

    diagnostics = parse_error_diffs(stdout, _parse_file_path, logger=reporter.logger)
    reporter.report_diagnostics(list(diagnostics))

    return ret


def _create_ruff_command(
    setting_path: pathlib.Path,
    subcommand: str,
    targets: List[str],
    flags: List[str],
) -> List[str]:
    return ["ruff", "--config", str(setting_path), subcommand] + targets + flags


def run(
    reporter: Reporter,
    base_dir: pathlib.Path,
    setting_path: pathlib.Path,
    sources: Iterable[pathlib.Path],
    inplace_edit: bool,
) -> int:
    targets = [str(d) for d in sources]
    if len(targets) == 0:
        return 0

    if inplace_edit:
        # - `ruff check --fix`
        # - `ruff format`
        # this is horrible CLI design since `pysen run format` would actually "fix" violations reported in `pysen run lint`
        lint_ret = _run_command_and_report(
            _create_ruff_command(setting_path, "check", targets, ["--fix"]),
            reporter,
            base_dir,
        )
        format_ret = _run_command_and_report(
            _create_ruff_command(setting_path, "format", targets, []),
            reporter,
            base_dir,
        )
        return max(lint_ret, format_ret)
    else:
        # - `ruff check --diff` to lint code
        # - `ruff format --check` to show formatting diffs
        lint_ret = _run_command_and_report(
            _create_ruff_command(setting_path, "check", targets, ["--diff"]),
            reporter,
            base_dir,
        )
        format_ret = _run_command_and_report(
            _create_ruff_command(setting_path, "format", targets, ["--diff"]),
            reporter,
            base_dir,
        )
        return max(lint_ret, format_ret)
