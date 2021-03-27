from pathlib import Path
from unittest import mock

from pysen.error_lines import parse_error_diffs, parse_error_lines
from pysen.ext.black_wrapper import _parse_file_path

std_err1 = "/path/to/file1.py:70:5: error: Missing return statement [return]\n"
std_err2 = "/path/to/file2.py:71:6: error: Missing return statement [return]\n"
std_err = "".join([std_err1, std_err2])
mypy_invalid_format = (
    "/home/user/pysen/__init__.py:72: error: unused 'type: ignore' comment\n"
)


diff_err1 = """--- /tmp/tmp.py      2020-05-29 13:45:10.907383 +0000
+++ /tmp/tmp.py      2020-05-29 13:45:12.563367 +0000
@@ -1,7 +1,8 @@
 class Hoge:
-    a=3
+    a = 3
+
 
 for a in range(3):
     print(a)
 
 for b in range(3):
@@ -17,6 +18,7 @@
     print(a)
 
 for b in range(3):
     print(b)
 
-answer_to_everything=42
+answer_to_everything = 42
+
"""  # NOQA

diff_err2 = """--- /home/user/pysen/pysen/cli.py  2020-06-10 05:31:01.167304 +0000
+++ /home/user/pysen/pysen/cli.py  2020-06-10 05:35:33.973467 +0000
@@ -147,10 +147,11 @@
     )
     parser.add_argument(
         "--version", action="store_true", help="Show pysen version and exit",
     )
     import math
+
     parser.add_argument(
         "--loglevel", type=str, help="Set loglevel", choices=list(LogLevel.__members__),
     )
     return parser

"""  # NOQA

diff_err3 = """--- /home/user/pysen/pysen/cli.py  2020-06-10 05:31:01.167304 +0000
+++ /home/user/pysen/pysen/cli.py  2020-06-10 05:35:33.973467 +0000
@@ -147,10 +147,9 @@
     )
     parser.add_argument(
         "--version", action="store_true", help="Show pysen version and exit",
     )
     import math
-
     parser.add_argument(
         "--loglevel", type=str, help="Set loglevel", choices=list(LogLevel.__members__),
     )
     return parser

"""  # NOQA

diff_err4 = """--- /home/user/pysen/foo.py        2021-03-25 16:43:53.875256 +0000
+++ /home/user/pysen/foo.py        2021-03-25 16:44:02.267033 +0000
@@ -1,8 +1,5 @@
 {
     foo: "",
-
-
     bar: [],
-
     baz: {},
 }
"""  # NOQA


def test_standard_parser() -> None:
    err1, err2 = parse_error_lines(std_err)

    assert err1.file_path == Path("/path/to/file1.py")
    assert err1.start_line == 70
    assert err1.end_line == 70
    assert err1.start_column == 5
    assert err1.message == "error: Missing return statement [return]"

    assert err2.file_path == Path("/path/to/file2.py")
    assert err2.start_line == 71
    assert err2.end_line == 71
    assert err2.start_column == 6
    assert err2.message == "error: Missing return statement [return]"

    err3 = list(parse_error_lines(mypy_invalid_format))[0]

    assert err3.file_path == Path("/home/user/pysen/__init__.py")
    assert err3.start_line == 72
    assert err3.end_line == 72
    assert err3.start_column is None
    assert err3.message == "error: unused 'type: ignore' comment"

    with mock.patch("pysen.error_lines._warn_parse_error") as warn:
        error = "invalid_format\n"
        list(parse_error_lines(error))
        warn.assert_called_with(error.rstrip("\n"), None)

    logger = mock.Mock()
    with mock.patch("pysen.error_lines._warn_parse_error") as warn:
        error = "invalid_format\n"
        list(parse_error_lines(error, logger))
        warn.assert_called_with(error.rstrip("\n"), logger)


def test_diff_parser() -> None:
    err1, err2 = parse_error_diffs(diff_err1, _parse_file_path)

    assert err1.start_line == 2
    assert err1.end_line == 2
    assert err1.start_column == 1
    assert err1.file_path == Path("/tmp/tmp.py")
    assert err1.diff == "-    a=3\n+    a = 3\n+\n"

    assert err2.start_line == 22
    assert err2.end_line == 22
    assert err2.start_column == 1
    assert err2.file_path == Path("/tmp/tmp.py")
    assert err2.diff == "-answer_to_everything=42\n+answer_to_everything = 42\n+\n"
    with mock.patch("pysen.error_lines._warn_parse_error") as warn:
        diff = "---/tmp/tmp.py\n+++/tmp/tmp.py\n@@ -1,7 +1,8 @@\ninvalid\n"
        list(parse_error_diffs(diff, _parse_file_path))
        warn.assert_called_with(diff, None)

    logger = mock.Mock()
    with mock.patch("pysen.error_lines._warn_parse_error") as warn:
        diff = "---/tmp/tmp.py\n+++/tmp/tmp.py\n@@ -1,7 +1,8 @@\ninvalid\n"
        list(parse_error_diffs(diff, _parse_file_path, logger))
        warn.assert_called_with(diff, logger)

    # has only target diff
    errors = list(parse_error_diffs(diff_err2, _parse_file_path))
    assert len(errors) == 1
    err = errors[0]
    assert err.start_line == 152
    assert err.end_line == 152
    assert err.diff == "+\n     parser.add_argument(\n"

    # has only source diff
    errors = list(parse_error_diffs(diff_err3, _parse_file_path))
    assert len(errors) == 1
    err = errors[0]
    assert err.start_line == 152
    assert err.end_line == 152
    assert err.diff == "-\n\n"

    # has multiple deletion
    errors = list(parse_error_diffs(diff_err4, _parse_file_path))

    assert len(errors) == 1
    err1 = errors[0]
    assert err1.start_line == 3
    assert err1.end_line == 6
    assert err1.diff == "-\n-\n     bar: [],\n-\n"
