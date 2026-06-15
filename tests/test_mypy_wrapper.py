import pathlib
from unittest import mock

import pytest

from pysen.exceptions import IncompatibleVersionError
from pysen.ext.mypy_wrapper import MypyPlugin, MypyTarget, _check_mypy_version, run
from pysen.reporter import Reporter

BASE_DIR = pathlib.Path(__file__).resolve().parent


def test_run_zero_source() -> None:
    reporter = Reporter("mypy")
    assert run(reporter, BASE_DIR, BASE_DIR, MypyTarget([]), True) == 0


def test__check_mypy_version() -> None:
    def check(version: str) -> None:
        _check_mypy_version.cache_clear()
        with mock.patch(
            "pysen.dist_version.distribution",
            return_value=mock.Mock(version=version),
        ):
            _check_mypy_version()

    # supported: >=0.770, <3
    check("0.770")
    check("0.991")
    check("1.19.0")
    check("2.0.0")
    check("2.1.0")

    # unsupported
    for version in ("0.760", "3.0.0"):
        with pytest.raises(IncompatibleVersionError):
            check(version)


def test_mypy_plugin() -> None:
    script_plugin = MypyPlugin(script=pathlib.Path("/foo/bar/baz"))
    script_plugin2 = MypyPlugin(script=pathlib.Path("./bar/baz"))
    function_plugin = MypyPlugin(function="module_x")
    function_plugin2 = MypyPlugin(function="module_x:entry")

    with pytest.raises(ValueError):
        MypyPlugin()

    with pytest.raises(ValueError):
        MypyPlugin(script=pathlib.Path("."), function="module_y")

    assert script_plugin.as_config() == "/foo/bar/baz"
    assert script_plugin2.as_config() == "bar/baz"
    assert function_plugin.as_config() == "module_x"
    assert function_plugin2.as_config() == "module_x:entry"

    base_dir = pathlib.Path("/foo")
    assert function_plugin.as_config(base_dir) == "module_x"
    assert function_plugin2.as_config(base_dir) == "module_x:entry"
    assert script_plugin.as_config(base_dir) == "bar/baz"
    assert script_plugin2.as_config(base_dir) == "bar/baz"

    base_dir = pathlib.Path("/hoge")
    assert script_plugin.as_config(base_dir) == "../foo/bar/baz"
    assert script_plugin2.as_config(base_dir) == "bar/baz"
