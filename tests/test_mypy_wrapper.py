import pathlib

import pytest

from pysen.ext.mypy_wrapper import MypyPlugin, MypyTarget, run
from pysen.reporter import Reporter

BASE_DIR = pathlib.Path(__file__).resolve().parent


def test_run_zero_source() -> None:
    reporter = Reporter("mypy")
    assert run(reporter, BASE_DIR, BASE_DIR, MypyTarget([]), True) == 0


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
