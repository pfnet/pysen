import collections
import pathlib
from typing import DefaultDict, Iterator
from unittest import mock

import pytest

from pysen import mypy
from pysen.mypy import _get_differences_from_base
from pysen.process_utils import add_python_executable
from pysen.reporter import Reporter
from pysen.runner_options import PathContext, RunOptions
from pysen.setting import SettingFile

BASE_DIR = pathlib.Path(__file__).resolve().parent


@pytest.fixture
def reporter() -> Iterator[Reporter]:
    r = Reporter("")
    with r:
        yield r


def test__get_differences_from_base() -> None:
    A = {"A": "a", "B": "b", "C": "c", "X": ["1", "2", "3"], "Y": ["a", "b"]}
    B = {"A": "a", "C": "c2", "D": "d", "X": ["1", "2", "3"], "Y": ["a", "c"]}

    assert _get_differences_from_base(A, B) == {"B": "b", "C": "c", "Y": ["a", "b"]}
    assert _get_differences_from_base(B, A) == {"C": "c2", "D": "d", "Y": ["a", "c"]}


def test_mypy_setting() -> None:
    s = mypy.MypySetting.very_strict()
    assert s == mypy.MypySetting.very_strict()
    assert s != mypy.MypySetting.strict()

    section, settings = s.export(BASE_DIR)
    assert section == ["mypy"]
    assert settings["check_untyped_defs"]
    assert "target_module" not in settings

    s.check_untyped_defs = False
    section, settings = s.export(BASE_DIR)
    assert not settings["check_untyped_defs"]

    section, settings = s.export(BASE_DIR, target_module="hoge.fuga.*")
    assert section == ["mypy-hoge.fuga.*"]

    s.mypy_path = [
        "/opt/pysen/stubs",
        "stubs2",
        pathlib.Path("/usr/pysen/stubs3"),
        pathlib.Path("stub4"),
    ]
    section, settings = s.export(pathlib.Path("/opt/pysen/package/python"))
    assert settings["mypy_path"] == [
        "/opt/pysen/stubs",
        "stubs2",
        "/usr/pysen/stubs3",
        "stub4",
    ]

    # This option is set by pyproject loader
    s._pysen_convert_abspath = True
    section, settings = s.export(pathlib.Path("/opt/pysen/package/python"))
    assert settings["mypy_path"] == [
        "../../stubs",
        "stubs2",
        "../../../../usr/pysen/stubs3",
        "stub4",
    ]


def test_settings() -> None:
    m = mypy.Mypy(
        setting=mypy.MypySetting.very_strict(),
        module_settings={"hoge.fuga": mypy.MypySetting.strict()},
    )
    assert m.setting == mypy.MypySetting.very_strict()
    assert m.module_settings == {"hoge.fuga": mypy.MypySetting.strict()}

    m = mypy.Mypy()
    assert m.setting == mypy.MypySetting()
    assert m.module_settings == {}


def test_commands(reporter: Reporter) -> None:
    m = mypy.Mypy(
        mypy_targets=[mypy.MypyTarget([pathlib.Path("/bar"), pathlib.Path("baz")])]
    )
    expected_cmds = add_python_executable(
        "mypy",
        "--show-absolute-path",
        "--no-color-output",
        "--show-column-numbers",
        "--no-error-summary",
        "--config-file",
        "/setting/setup.cfg",
        "/bar",
        "/foo/baz",
    )
    cmd = m.create_command(
        "lint",
        PathContext(pathlib.Path("/foo"), pathlib.Path("/setting")),
        RunOptions(),
    )

    with mock.patch("os.chdir", return_value=None):
        with mock.patch("pysen.process_utils.run", return_value=(0, "", "")) as patch:
            assert cmd(reporter=reporter) == 0
            patch.assert_called_with(expected_cmds, reporter)


def test_export_settings() -> None:
    m = mypy.Mypy(
        setting=mypy.MypySetting(
            mypy_path=["hoge"],
            plugins=[mypy.MypyPlugin(script=BASE_DIR / pathlib.Path("foo/bar"))],
            disallow_any_decorated=False,
            exclude="excluded",
            ignore_missing_imports=False,
            warn_redundant_casts=True,
            follow_imports=mypy.MypyFollowImports.ERROR,
            _pysen_convert_abspath=True,
        ),
        module_settings={
            "foo.*": mypy.MypySetting(disallow_any_decorated=True),  # duplicated
            "bar.baz": mypy.MypySetting(
                ignore_missing_imports=True,  # duplicated
                disallow_any_decorated=False,  # same (not emitted in exported settings)
                disallow_any_unimported=False,  # new
            ),
        },
    )
    files: DefaultDict[str, SettingFile] = collections.defaultdict(SettingFile)
    m.export_settings(PathContext(BASE_DIR, BASE_DIR), files)

    assert files.keys() == {"setup.cfg"}
    setting_file = files["setup.cfg"]
    expected = {
        "mypy": {
            "disallow_any_decorated": False,
            "exclude": "excluded",
            "follow_imports": "error",
            "ignore_missing_imports": False,
            "mypy_path": ["hoge"],
            "warn_redundant_casts": True,
            "plugins": ["foo/bar"],
        },
        "mypy-foo.*": {"disallow_any_decorated": True},
        "mypy-bar.baz": {
            "disallow_any_unimported": False,
            "ignore_missing_imports": True,
        },
    }

    assert setting_file.as_dict() == expected
