import dataclasses
import pathlib
import tempfile
from typing import Callable, Iterator, Optional

import dacite
import pytest

from pysen import pyproject
from pysen.black import Black
from pysen.exceptions import InvalidConfigurationError
from pysen.isort import Isort, IsortSectionName
from pysen.manifest import Manifest
from pysen.mypy import Mypy, MypyFollowImports, MypyPreset
from pysen.path import change_dir
from pysen.pyproject_model import Config, LintConfig
from pysen.source import Source

FILE_PATH = pathlib.Path(__file__).resolve()
BASE_DIR = FILE_PATH.parent
ROOT_DIR = BASE_DIR.parent

PYPROJECT_PATH = ROOT_DIR / "pyproject.toml"
EXAMPLE_DIR = ROOT_DIR / "examples/simple_package"
EXAMPLE_PYPROJECT_PATH = EXAMPLE_DIR / "pyproject.toml"

assert PYPROJECT_PATH.exists()
assert EXAMPLE_DIR.exists()
assert EXAMPLE_PYPROJECT_PATH.exists()


@pytest.fixture
def temp_dir() -> Iterator[pathlib.Path]:
    with tempfile.TemporaryDirectory() as td:
        yield pathlib.Path(td)


def test_find_pyproject() -> None:
    with change_dir(BASE_DIR):
        assert pyproject.find_pyproject() == PYPROJECT_PATH

    with change_dir(BASE_DIR / "fakes/configs"):
        assert pyproject.find_pyproject() == PYPROJECT_PATH

    with change_dir(EXAMPLE_DIR):
        assert pyproject.find_pyproject() == EXAMPLE_PYPROJECT_PATH

    with pytest.raises(FileNotFoundError):
        pyproject.find_pyproject(BASE_DIR)

    with pytest.raises(FileNotFoundError):
        pyproject.find_pyproject(BASE_DIR / "no_such_file")

    assert pyproject.find_pyproject(FILE_PATH) == FILE_PATH


def test_load_manifest() -> None:
    manifest = pyproject.load_manifest(BASE_DIR / "fakes/configs/example.toml")
    assert manifest is not None
    assert isinstance(manifest, Manifest)
    components = manifest.components
    assert {x.name for x in components} == {
        "black",
        "isort",
        "mypy",
        "create_component1",
        "create_component2",
    }
    mypy = manifest.get_component("mypy")
    assert isinstance(mypy, Mypy)
    assert mypy.setting.mypy_path == [BASE_DIR / "fakes/configs/pysen-stubs"]

    assert mypy.setting.plugins is not None
    assert len(mypy.setting.plugins) == 2
    assert mypy.setting.plugins[0].script == BASE_DIR / "fakes/configs" / pathlib.Path(
        "./sugoi/plugin"
    )
    assert mypy.setting.plugins[1].function == "sugoi_plugin:entry"

    assert mypy.setting._pysen_convert_abspath

    module_settings = mypy.module_settings
    assert len(module_settings) == 4
    assert module_settings.keys() == {"pysen.stubs", "pysen.proto", "apple", "banana"}
    assert module_settings["pysen.stubs"].ignore_errors
    assert module_settings["pysen.proto"].ignore_errors
    assert not module_settings["apple"].ignore_errors
    assert module_settings["banana"].ignore_errors

    entry_setting = MypyPreset.ENTRY.get_setting(
        follow_imports=MypyFollowImports.SILENT
    )
    entry_setting._pysen_convert_abspath = True
    assert module_settings["apple"] == entry_setting

    isort = manifest.get_component("isort")
    assert isinstance(isort, Isort)
    assert isort.setting.default_section == IsortSectionName.THIRDPARTY

    manifest = pyproject.load_manifest(BASE_DIR / "fakes/configs/simple_source.toml")
    assert manifest is not None
    assert isinstance(manifest, Manifest)
    components = manifest.components
    assert len(components) == 1
    assert {x.name for x in components} == {"mypy"}

    manifest = pyproject.load_manifest(BASE_DIR / "fakes/configs/builder.toml")
    assert manifest is not None
    assert isinstance(manifest, Manifest)
    components = manifest.components
    assert len(components) == 2
    assert {x.name for x in components} == {"flake8", "isort"}


def test_resolve_lint_config_inheritance() -> None:
    source = Source(includes=[BASE_DIR])
    success = LintConfig(
        base=pathlib.Path(BASE_DIR / "fakes/configs/base.toml"),
        isort_known_first_party=["alpha"],
        source=source,
    )
    config = pyproject.resolve_lint_config_inheritance(success)
    assert config.isort_known_third_party == ["fuga", "piyo"]  # override by base.toml
    assert config.isort_known_first_party == ["alpha"]  # override by us
    assert config.line_length == 88  # override by base.toml

    failure_empty = LintConfig(
        base=pathlib.Path(BASE_DIR / "fakes/configs/empty.toml"),
        isort_known_first_party=["alpha"],
        source=source,
    )
    with pytest.raises(InvalidConfigurationError) as ex:
        pyproject.resolve_lint_config_inheritance(failure_empty)
    assert "doesn't have [tool.pysen.lint] section." in str(ex.value)


def test_load_lint_components() -> None:
    source = Source(includes=[BASE_DIR])
    success = LintConfig(
        base=pathlib.Path(BASE_DIR / "fakes/configs/base.toml"),
        isort_known_first_party=["alpha"],
        source=source,
    )
    components = pyproject.load_lint_components(success)
    assert len(components) == 2
    isort = next(x for x in components if isinstance(x, Isort))  # from base.toml
    black = next(x for x in components if isinstance(x, Black))  # from base2.toml
    assert isort is not None
    assert black is not None
    assert isort.setting.known_third_party == {"fuga", "piyo"}  # override by base.toml
    assert isort.setting.known_first_party == {"alpha"}  # override by us
    assert black.setting.line_length == 88  # override by base.toml

    failure_empty = LintConfig(
        base=pathlib.Path(BASE_DIR / "fakes/configs/empty.toml"),
        isort_known_first_party=["alpha"],
        source=source,
    )
    with pytest.raises(InvalidConfigurationError) as ex:
        pyproject.load_lint_components(failure_empty)
    assert "doesn't have [tool.pysen.lint] section." in str(ex.value)


def test_resolve_inheritance() -> None:
    @dataclasses.dataclass
    class _Model:
        message: str
        base: Optional[str] = None

    def selector(name: str) -> Callable[[pathlib.Path, Config], _Model]:
        section_path = f"tool.pysen.plugin.{name}"

        def impl(path: pathlib.Path, root: Config) -> _Model:
            config: Optional[_Model] = None
            if root.plugin is not None:
                target = next(
                    (x for x in root.plugin if x.location == section_path), None
                )
                if target is not None and target.config is not None:
                    config = dacite.from_dict(
                        _Model, target.config, dacite.Config(strict=True)
                    )
                    assert isinstance(config, _Model)

            if config is None:
                raise RuntimeError(f"doesn't have [{section_path}] section")

            return config

        return impl

    def base_selector(path: pathlib.Path, config: _Model) -> Optional[pathlib.Path]:
        if config.base is None:
            return None
        return BASE_DIR / "fakes/configs" / config.base

    def updater(lhs: _Model, rhs: _Model) -> _Model:
        lhs.message = f"{lhs.message} / {rhs.message}"
        return lhs

    config = pyproject.resolve_inheritance(
        BASE_DIR / "fakes/configs/base.toml", selector("ok"), base_selector, updater
    )
    assert config.message == "hello ok from base2 / hello ok from base"

    with pytest.raises(RuntimeError) as ex:
        pyproject.resolve_inheritance(
            BASE_DIR / "fakes/configs/base.toml",
            selector("error-nosection"),
            base_selector,
            updater,
        )

    assert "doesn't have [tool.pysen.plugin.error-nosection]" in str(ex.value)

    with pytest.raises(FileNotFoundError):
        pyproject.resolve_inheritance(
            BASE_DIR / "fakes/configs/base.toml",
            selector("error-nofile"),
            base_selector,
            updater,
        )

    base3 = BASE_DIR / "fakes/configs/base3.toml"
    with pytest.raises(InvalidConfigurationError) as e:
        pyproject.resolve_inheritance(base3, selector("ok"), base_selector, updater)
    assert f"Circular dependency detected. {base3} was visited more than once." in str(
        e
    )


def test__check_section_exists(temp_dir: pathlib.Path) -> None:
    test_file = temp_dir / "foo.toml"
    test_file.write_text("x = 0")
    assert not pyproject._check_section_exists(test_file)

    test_file.write_text(
        """[tool]
x = 0"""
    )
    assert not pyproject._check_section_exists(test_file)

    test_file.write_text(
        """[tool.pysen]
x = 0"""
    )
    assert pyproject._check_section_exists(test_file)

    test_file.write_text(
        """[tool.pysen2]
x = 0"""
    )
    assert not pyproject._check_section_exists(test_file)

    test_file.write_text(
        """[tool.pysen]
x = 0
[tool.foo]
y = 1"""
    )
    assert pyproject._check_section_exists(test_file)


def test_find_config(temp_dir: pathlib.Path) -> None:
    pysen_config = """[tool.pysen]
x = 0"""
    other_config = """[tool.foo]
x = 0"""

    pyproject_file = temp_dir / "pyproject.toml"
    pysen_file = temp_dir / "pysen.toml"
    other_file = temp_dir / "foo.toml"

    other_file.write_text(pysen_config)
    assert pyproject.find_config(temp_dir) is None

    pyproject_file.write_text(other_config)
    assert pyproject.find_config(temp_dir) is None

    pyproject_file.write_text(pysen_config)
    assert pyproject.find_config(temp_dir) == pyproject_file

    # checks that the config resolution order is pysen_file -> pyproject_file
    pysen_file.write_text(pysen_config)
    assert pyproject.find_config(temp_dir) == pysen_file

    pysen_file.write_text(other_config)
    assert pyproject.find_config(temp_dir) == pyproject_file


def test_find_config_recursive(temp_dir: pathlib.Path) -> None:
    assert pyproject.find_config_recursive(BASE_DIR) == PYPROJECT_PATH
    assert pyproject.find_config_recursive(BASE_DIR / "fakes/configs") == PYPROJECT_PATH
    assert pyproject.find_config_recursive(EXAMPLE_DIR) == EXAMPLE_PYPROJECT_PATH
    assert pyproject.find_config_recursive(temp_dir) is None

    temp_pyproject = temp_dir / "pyproject.toml"
    temp_pyproject.write_text(
        """[tool.pysen]
x = 1"""
    )
    assert pyproject.find_config_recursive(temp_dir) == temp_pyproject
