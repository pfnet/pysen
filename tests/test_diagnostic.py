from pathlib import Path

import pytest

from pysen.diagnostic import Diagnostic, FLCMFormatter, _format_diagnostic_position


def test_diagnostic_post_init() -> None:
    path = Path("/path/to/file")
    Diagnostic(file_path=path, message="error")
    Diagnostic(file_path=path, diff="diff")
    with pytest.raises(ValueError):
        Diagnostic(file_path=path)


def test_diagnostic_formatter() -> None:
    path = Path("/path/to/file")
    formatter = FLCMFormatter
    err = formatter.format(
        Diagnostic(
            start_line=10,
            end_line=12,
            start_column=3,
            file_path=path,
            message="line1\nline2",
        ),
        "my_command",
    )
    assert err == f"{path.resolve()}:10:3:my_command: line1\\nline2"

    err = formatter.format(
        Diagnostic(
            start_line=10,
            end_line=12,
            start_column=3,
            file_path=path,
            diff="-line1\n+line2\n",
        ),
        "my_command2",
    )
    assert err == f"{path.resolve()}:10:3:my_command2: -line1\\n+line2\\n"


def test__format_diagnostic_position() -> None:
    path = Path("/path/to/file")
    position = _format_diagnostic_position(
        Diagnostic(start_line=10, end_line=12, start_column=3, file_path=path, diff="")
    )
    assert position == f"{path.resolve()}:10:3"

    position = _format_diagnostic_position(Diagnostic(file_path=path, diff=""))
    assert position == f"{path.resolve()}:1:1"
