import logging
import pathlib
from typing import Any, List

import dacite
import pytest
import tomlkit
from _pytest.logging import LogCaptureFixture

from pysen.factory import MypyModuleOption
from pysen.isort import IsortSectionName
from pysen.mypy import MypyFollowImports, MypyPreset
from pysen.py_version import PythonVersion, VersionRepresentation
from pysen.pyproject_model import (
    Config,
    InvalidConfigurationError,
    LintConfig,
    _load_version,
    _migrate_alias_fields,
    _migrate_deprecated_fields,
    _parse_mypy_modules,
    _parse_mypy_target,
    _parse_mypy_targets,
    _parse_plugin_configs,
    _parse_python_version,
    _parse_source,
    has_tool_section,
    parse,
)
from pysen.source import SourceEntrySetting

BASE_DIR = pathlib.Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "fakes/configs"


def test__parse_plugin_configs() -> None:
    data_x = {
        "script": "hoge.py",
    }
    data_y = {
        "function": "foo.bar::baz",
        "config": {"message": "hello"},
    }
    data = {
        "X": data_x,
        "Y": data_y,
    }

    configs = _parse_plugin_configs(BASE_DIR, data)

    assert len(configs) == 2
    assert configs[0].location == "tool.pysen.plugin.X"
    assert configs[1].location == "tool.pysen.plugin.Y"
    assert configs[0].script == BASE_DIR / "hoge.py"
    assert configs[1].script is None
    assert configs[0].function is None
    assert configs[1].function == "foo.bar::baz"

    assert configs[0].config is None
    assert configs[1].config == {
        "message": "hello",
    }

    data_invalid_path = {
        "location": "donot set this section from pyproject",
        "script": "hoge.py",
    }
    with pytest.raises(dacite.DaciteError) as ex:
        _parse_plugin_configs(BASE_DIR, {"X": data_invalid_path})
    assert "unknown filed" in str(ex.value)

    data_invalid_no_plugin = {
        "config": {"message": "hello"},
    }
    with pytest.raises(dacite.DaciteError) as ex:
        _parse_plugin_configs(BASE_DIR, {"X": data_invalid_no_plugin})
    assert "must specify" in str(ex.value)

    data_invalid_both = {
        "function": "foo.bar::baz",
        "script": "hoge.py",
        "config": {"message": "hello"},
    }
    with pytest.raises(dacite.DaciteError) as ex:
        _parse_plugin_configs(BASE_DIR, {"X": data_invalid_both})
    assert "only one of" in str(ex.value)

    with pytest.raises(dacite.WrongTypeError):
        _parse_plugin_configs(BASE_DIR, [])


def test__parse_source() -> None:
    source = _parse_source(BASE_DIR, ["foo", "bar/baz"])
    assert len(source.includes) == 2
    assert source.includes.keys() == {BASE_DIR / "foo", BASE_DIR / "bar/baz"}
    assert all(not x.glob for x in source.includes.values())

    source = _parse_source(
        BASE_DIR,
        {
            "includes": ["foo"],
            "include_globs": ["bar/*.template"],
            "excludes": ["hoge"],
            "exclude_globs": ["fuga/*_grpc.py"],
        },
    )
    includes = source.includes
    assert len(includes) == 2
    assert includes.keys() == {BASE_DIR / "foo", "bar/*.template"}
    assert not includes[BASE_DIR / "foo"].glob
    assert includes["bar/*.template"].glob
    assert includes["bar/*.template"].base_dir == BASE_DIR

    excludes = source.excludes
    assert len(excludes) == 2
    assert excludes.keys() == {BASE_DIR / "hoge", "fuga/*_grpc.py"}
    assert not excludes[BASE_DIR / "hoge"].glob
    assert excludes["fuga/*_grpc.py"].glob
    assert excludes["fuga/*_grpc.py"].base_dir == BASE_DIR

    source = _parse_source(
        BASE_DIR,
        {"excludes": ["hoge"], "exclude_globs": ["fuga/*_grpc.py"]},
    )

    includes = source.includes
    assert len(includes) == 1
    assert includes.keys() == {"."}
    assert not includes["."].glob
    assert includes["."].base_dir == BASE_DIR

    excludes = source.excludes
    assert len(excludes) == 2
    assert excludes.keys() == {BASE_DIR / "hoge", "fuga/*_grpc.py"}

    with pytest.raises(dacite.DaciteError):
        _parse_source(BASE_DIR, 1.0)


def test__parse_python_version() -> None:
    assert _parse_python_version("py37") == PythonVersion(3, 7)
    assert _parse_python_version("PY38") == PythonVersion(3, 8)
    with pytest.raises(dacite.DaciteError) as ex:
        _parse_python_version("PY999")

    assert "one of" in str(ex.value)  # ensure that we suggest some options

    with pytest.raises(dacite.WrongTypeError):
        _parse_python_version(37)


def test__parse_mypy_target() -> None:
    base_dir = pathlib.Path("/foo")

    with pytest.raises(dacite.DaciteError):
        _parse_mypy_target(base_dir, "a")

    with pytest.raises(dacite.DaciteError):
        _parse_mypy_target(base_dir, {"paths": []})

    target = _parse_mypy_target(base_dir, {"paths": ["a", "b", "/d"]})
    assert target.paths == [base_dir / "a", base_dir / "b", pathlib.Path("/d")]

    target = _parse_mypy_target(base_dir, {"paths": ["a"], "namespace_packages": True})
    assert target.paths == [base_dir / "a"]
    assert target.namespace_packages


def test__parse_mypy_targets() -> None:
    base_dir = pathlib.Path("/foo")

    with pytest.raises(dacite.DaciteError) as e:
        _parse_mypy_targets(base_dir, ["a", "b", "/c"])

    base_dir = pathlib.Path("/foo")
    test_data: List[Any] = [{"paths": ["x", "/y", "z"]}, {"paths": ["a", "b"]}]
    targets = _parse_mypy_targets(base_dir, test_data)
    assert len(targets) == 2
    assert targets[0].paths == [base_dir / "x", pathlib.Path("/y"), base_dir / "z"]
    assert targets[1].paths == [base_dir / "a", base_dir / "b"]

    test_data.append("x")
    with pytest.raises(dacite.DaciteError) as e:
        _parse_mypy_targets(base_dir, test_data)

    assert "tool.pysen.lint.mypy_targets must be a list of dicts" in str(e.value)


def test__parse_mypy_modules() -> None:
    with pytest.raises(dacite.WrongTypeError):
        _parse_mypy_modules("x")

    assert _parse_mypy_modules({}) == {}

    modules = _parse_mypy_modules({"a": {}, "b": {}})
    assert modules.keys() == {"a", "b"}
    assert not modules["a"].ignore_errors
    assert not modules["b"].ignore_errors
    assert modules["a"].preset is None
    assert modules["b"].preset is None

    with pytest.raises(dacite.WrongTypeError):
        _parse_mypy_modules({"a": "b"})

    with pytest.raises(dacite.WrongTypeError):
        _parse_mypy_modules({1: {}})

    modules = _parse_mypy_modules(
        {"a": {"preset": "entry"}, "b.c": {"ignore_errors": True}}
    )
    assert modules.keys() == {"a", "b.c"}
    assert not modules["a"].ignore_errors
    assert modules["b.c"].ignore_errors
    assert modules["a"].preset == MypyPreset.ENTRY
    assert modules["b.c"].preset is None

    with pytest.raises(dacite.DaciteError) as e:
        _parse_mypy_modules({"a.b.c": {"preset": "entry", "ignore_errors": True}})

    assert "a.b.c" in str(e.value)


def test__migrate_alias_fields() -> None:
    config = Config(lint=None)
    _migrate_alias_fields(config)
    assert config.lint is None

    config = Config(lint=LintConfig(mypy_ignore_packages=["X", "Y.Z.*"]))
    _migrate_alias_fields(config)
    assert config.lint is not None
    assert config.lint.mypy_ignore_packages is None
    assert config.lint.mypy_modules is not None
    assert config.lint.mypy_modules.keys() == {"X", "Y.Z.*"}
    assert config.lint.mypy_modules["X"].ignore_errors
    assert config.lint.mypy_modules["Y.Z.*"].ignore_errors

    config = Config(
        lint=LintConfig(
            mypy_ignore_packages=["X"], mypy_modules={"X": MypyModuleOption()}
        )
    )
    with pytest.raises(dacite.DaciteError) as e:
        _migrate_alias_fields(config)

    assert "X is configured in both mypy_ignore_packages and mypy_modules" in str(
        e.value
    )


def test__migrate_deprecated_fields(caplog: LogCaptureFixture) -> None:
    base_dir = pathlib.Path("/foo")
    setting_path = pathlib.Path("/foo/pyproject.toml")

    caplog.clear()
    config = Config(lint=None)
    _migrate_deprecated_fields(setting_path, config)
    assert config.lint is None
    assert caplog.records == []

    config = Config(
        lint=LintConfig(
            mypy_target_dirs=[base_dir / "a", base_dir / "b", base_dir / "c"]
        ),
    )
    _migrate_deprecated_fields(setting_path, config)
    assert config.lint is not None
    assert config.lint.mypy_target_dirs is None
    assert config.lint.mypy_targets is not None and len(config.lint.mypy_targets) == 1
    assert config.lint.mypy_targets[0].paths == [
        base_dir / "a",
        base_dir / "b",
        base_dir / "c",
    ]
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.WARNING
    assert "tool.pysen.mypy_target_dirs is deprecated" in record.message
    assert str(setting_path) in record.message


def test_example() -> None:
    config = parse(CONFIG_DIR / "example.toml")
    assert config is not None

    assert config.builder is None
    assert config.lint is not None
    lint = config.lint
    assert lint.enable_black
    assert not lint.enable_flake8
    assert lint.enable_isort
    assert lint.enable_mypy
    assert lint.line_length == 88
    assert isinstance(lint.line_length, int)
    assert lint.py_version == PythonVersion(3, 7)
    assert lint.isort_known_first_party == ["alpha"]
    assert lint.isort_known_third_party == ["beta", "gamma"]
    assert lint.isort_default_section == IsortSectionName.THIRDPARTY
    assert lint.mypy_modules is not None
    assert lint.mypy_modules.keys() == {"pysen.stubs", "pysen.proto", "apple", "banana"}
    assert lint.mypy_modules["pysen.stubs"].ignore_errors
    assert lint.mypy_modules["pysen.proto"].ignore_errors
    assert not lint.mypy_modules["apple"].ignore_errors
    assert lint.mypy_modules["banana"].ignore_errors

    assert lint.mypy_modules["pysen.stubs"].follow_imports == MypyFollowImports.SKIP
    assert lint.mypy_modules["pysen.proto"].follow_imports == MypyFollowImports.SKIP
    assert lint.mypy_modules["apple"].follow_imports == MypyFollowImports.SILENT
    assert lint.mypy_modules["banana"].follow_imports is None

    assert lint.mypy_modules["apple"].preset == MypyPreset.ENTRY
    assert lint.mypy_path == [CONFIG_DIR / "pysen-stubs"]

    assert lint.mypy_plugins is not None
    assert len(lint.mypy_plugins) == 2
    assert lint.mypy_plugins[0].script == CONFIG_DIR / pathlib.Path("./sugoi/plugin")
    assert lint.mypy_plugins[1].function == "sugoi_plugin:entry"

    assert lint.source is not None
    source = lint.source
    assert source.includes == {
        CONFIG_DIR: SourceEntrySetting(glob=False),
        CONFIG_DIR / "hoge": SourceEntrySetting(glob=False),
        "**/*.template": SourceEntrySetting(glob=True, base_dir=CONFIG_DIR),
    }
    assert source.excludes == {
        CONFIG_DIR / "fuga": SourceEntrySetting(glob=False),
        "foo/*_pb2.py": SourceEntrySetting(glob=True, base_dir=CONFIG_DIR),
    }


def test_simple_source() -> None:
    config = parse(CONFIG_DIR / "simple_source.toml")
    assert config is not None

    assert config.builder is None
    assert config.lint is not None
    lint = config.lint
    assert lint.enable_mypy
    assert lint.line_length == 80
    assert lint.py_version == PythonVersion(2, 7)
    assert lint.source is not None
    source = lint.source
    assert source.includes == {
        CONFIG_DIR: SourceEntrySetting(glob=False),
        CONFIG_DIR / "hoge": SourceEntrySetting(glob=False),
        CONFIG_DIR / "piyo": SourceEntrySetting(glob=False),
    }
    assert source.excludes == {}


def test_builder() -> None:
    config = parse(CONFIG_DIR / "builder.toml")
    assert config is not None

    assert config.lint is None
    assert config.builder is not None
    # check if builder is already resolved (is an abspath)
    assert config.builder.is_absolute()
    assert config.builder == CONFIG_DIR / "good_builder.py"


def test_plugin() -> None:
    config = parse(CONFIG_DIR / "plugin.toml")
    assert config is not None

    assert config.lint is None
    assert config.plugin is not None
    assert len(config.plugin) == 2
    assert config.plugin[0].location == "tool.pysen.plugin.hoge"
    assert config.plugin[0].script == CONFIG_DIR / "../plugin.py"
    assert config.plugin[0].function is None
    assert config.plugin[0].config is None

    assert config.plugin[1].location == "tool.pysen.plugin.fuga"
    assert config.plugin[1].script is None
    assert config.plugin[1].function == "fakes.plugins::create"
    assert config.plugin[1].config == {
        "message": "hello",
        "value": 10.0,
        "flag": False,
    }


def test_lint_config_update() -> None:
    lhs = LintConfig(
        base=pathlib.Path("hoge"),
        enable_black=True,
        enable_isort=True,
        line_length=80,
        isort_known_first_party=["hoge", "fuga"],
        isort_known_third_party=["piyo"],
    )
    rhs = LintConfig(
        base=pathlib.Path("fuga"),
        enable_black=False,
        enable_flake8=True,
        isort_known_first_party=["foo"],
        py_version=PythonVersion(3, 8),
    )

    lhs.update(rhs)

    assert lhs.base == pathlib.Path("hoge")
    assert not lhs.enable_black
    assert lhs.enable_flake8
    assert lhs.enable_isort
    assert not lhs.enable_mypy
    assert lhs.line_length == 80
    assert lhs.isort_known_first_party == ["foo"]
    assert lhs.isort_known_third_party == ["piyo"]
    assert lhs.py_version == PythonVersion(3, 8)


def test_has_tool_section() -> None:
    def _check_example_toml(tool_name: str, filename: str) -> bool:
        path = CONFIG_DIR / filename
        pyproject = tomlkit.loads(path.read_text())
        return has_tool_section(tool_name, pyproject)

    assert not _check_example_toml("pysen", "non_pysen_config.toml")
    assert not _check_example_toml("jiro", "non_pysen_config.toml")
    assert _check_example_toml("pysen", "base.toml")
    assert _check_example_toml("pysen", "base2.toml")
    assert _check_example_toml("pysen", "empty.toml")
    assert _check_example_toml("pysen", "example.toml")
    assert _check_example_toml("pysen", "builder.toml")
    assert _check_example_toml("pysen", "simple_source.toml")


def test___load_version() -> None:
    assert _load_version({}) is None
    assert _load_version({"version": "0.1.2a1"}) == VersionRepresentation(0, 1, 2, "a1")
    with pytest.raises(InvalidConfigurationError):
        _load_version({"version": "none"})
