import logging
import re
from pathlib import Path
from typing import Callable, Iterable, Optional

import unidiff

from pysen.diagnostic import Diagnostic
from pysen.exceptions import UnexpectedErrorFormat

FilePathParserType = Callable[[str], Path]
_logger = logging.getLogger(__name__)


def _warn_parse_error(errors: str, logger: Optional[logging.Logger]) -> None:
    logger = logger or _logger
    logger.warning(
        "The following error(s) could not be parsed, so pysen won't format it (them).\n"
        f"{errors}\n"
        f"If you think this is a bug please report it to the maintainers."
    )


def parse_error_lines(
    errors: str, logger: Optional[logging.Logger] = None
) -> Iterable[Diagnostic]:
    """
    Compatible with flake8, mypy
    """
    number = r"(?:0|[1-9]\d*)"
    _file_path = r"^(?P<file_path>.*?)"
    _line = fr":(?P<line>{number})"
    _column = fr"(:(?P<column>{number}))?"
    _message = r": (?P<message>.*$)"
    pattern = _file_path + _line + _column + _message
    invalid_lines = []
    for el in errors.splitlines():
        m = re.match(pattern, el)
        if m is None:
            invalid_lines.append(el)
            continue
        line = int(m.group("line"))
        if m.group("column") is None:
            column = None
        else:
            column = int(m.group("column"))
        yield Diagnostic(
            start_line=line,
            end_line=line,
            start_column=column,
            message=m.group("message").lstrip(" ").rstrip("\n"),
            file_path=Path(m.group("file_path")),
        )
    if invalid_lines:
        _warn_parse_error("\n".join(invalid_lines), logger)


def parse_error_diffs(
    errors: str,
    file_path_parser: FilePathParserType,
    logger: Optional[logging.Logger] = None,
) -> Iterable[Diagnostic]:
    """
    Compatible with isort, black
    """

    def _is_changed(line: unidiff.patch.Line) -> bool:
        return not line.is_context

    try:
        patches = unidiff.PatchSet(errors)
    except unidiff.errors.UnidiffParseError:
        _warn_parse_error(errors, logger)
        return
    for patch in patches:
        for hunk in patch:
            source_changes = list(filter(_is_changed, hunk.source_lines()))
            if source_changes:
                start_line = source_changes[0].source_line_no
                end_line = source_changes[-1].source_line_no
            else:
                target_changes = list(filter(_is_changed, hunk.target_lines()))
                assert target_changes, "expected either source or target line number"
                start_line = target_changes[0].target_line_no
                end_line = target_changes[-1].target_line_no

            try:
                file_path = file_path_parser(patch.source_file)
            except UnexpectedErrorFormat:
                _warn_parse_error(patch, logger)
                continue

            yield Diagnostic(
                start_line=start_line,
                end_line=end_line,
                start_column=1,
                file_path=file_path,
                diff="".join(map(str, filter(_is_changed, hunk))),
            )
