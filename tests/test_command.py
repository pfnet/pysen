import pathlib
import subprocess
import tempfile
import unittest.mock
from typing import Iterator, List

import pytest

from pysen.command import check_command_installed
from pysen.exceptions import CommandNotFoundError


@pytest.fixture
def invalid_command() -> Iterator[List[str]]:
    with tempfile.TemporaryDirectory() as td:
        yield [str(pathlib.Path(td) / "this_command_does_not_exist")]


def test_check_command_installed(invalid_command: List[str]) -> None:
    check_command_installed("echo", "a")

    with pytest.raises(CommandNotFoundError):
        check_command_installed(*invalid_command)
    with unittest.mock.patch("subprocess.call", return_value=127):
        with pytest.raises(CommandNotFoundError):
            assert subprocess.call("hoge") == 127
            check_command_installed("hoge")
