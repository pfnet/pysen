from pathlib import Path

from pysen.ext.black_wrapper import _parse_file_path


def test__parse_file_path() -> None:
    black_format = (
        "path/test_error_line_parser.py      2020-06-01 07:19:58.515112 +0000"
    )
    assert _parse_file_path(black_format) == Path("path/test_error_line_parser.py")
