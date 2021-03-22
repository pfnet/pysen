import dataclasses
import logging
import pathlib
from typing import Any, Dict, List, Optional

import dacite
import tomlkit

from ._version import __version__
from .exceptions import InvalidConfigurationError, PysenSectionNotFoundError
from .factory import ConfigureLintOptions, MypyModuleOption
from .isort import IsortSectionName
from .mypy import MypyFollowImports, MypyPreset, MypyTarget
from .py_version import PythonVersion, VersionRepresentation
from .source import Source

_logger = logging.getLogger(__name__)


@dataclasses.dataclass
class LintConfig(ConfigureLintOptions):
    base: Optional[pathlib.Path] = None

    # * Alias Fields *
    # config to create mypy_modules instances
    mypy_ignore_packages: Optional[List[str]] = None

    # * Deprecated Fields *
    mypy_target_dirs: Optional[List[pathlib.Path]] = None

    def update(self, rhs: "LintConfig") -> None:
        # NOTE(igarashi): do not overwrite base by rhs.base as it is required to refer
        fields = dataclasses.fields(self)
        for field in fields:
            field_name = field.name
            if field_name == "base":
                continue

            # NOTE(igarashi): handle None in rhs as "unset" state
            value = getattr(rhs, field_name)
            if value is not None:
                setattr(self, field_name, value)


@dataclasses.dataclass
class PluginConfig:
    # NOTE(igarashi): `location` is set from _parse_plugin_configs, not from pyproject.toml
    location: str = ""
    function: Optional[str] = None
    script: Optional[pathlib.Path] = None
    config: Optional[Dict[str, Any]] = None


@dataclasses.dataclass
class Config:
    version: Optional[VersionRepresentation] = None
    lint: Optional[LintConfig] = None
    builder: Optional[pathlib.Path] = None
    plugin: Optional[List[PluginConfig]] = None


PLUGIN_PATH_ROOT = "tool.pysen.plugin"


def _parse_plugin_configs(base_dir: pathlib.Path, data: Any) -> List[PluginConfig]:
    if data is None:
        return []

    if not isinstance(data, dict):
        raise dacite.WrongTypeError(dict, data, PLUGIN_PATH_ROOT)

    result: List[PluginConfig] = []

    for key, value in data.items():
        path = f"{PLUGIN_PATH_ROOT}.{key}"

        if not isinstance(value, dict):
            raise dacite.WrongTypeError(dict, value, path)

        # NOTE(igarashi): ensure that `location` is unspecified in pyproject.toml
        if "location" in value:
            raise dacite.DaciteError(f"unknown filed: {path}.location")

        config = dacite.from_dict(
            PluginConfig,
            value,
            config=dacite.Config(
                type_hooks={pathlib.Path: lambda x: _expand_path(base_dir, x)},
                strict=True,
            ),
        )
        assert isinstance(config, PluginConfig)
        config.location = path

        if config.function is None and config.script is None:
            raise dacite.DaciteError(
                "must specify either function or script for plugin field"
            )

        if config.function is not None and config.script is not None:
            raise dacite.DaciteError("only one of function or script must be speicifed")

        result.append(config)

    return result


def _parse_mypy_follow_imports(s: Any) -> MypyFollowImports:
    if not isinstance(s, str):
        raise dacite.WrongTypeError(MypyFollowImports, s)

    try:
        return MypyFollowImports[s.upper()]
    except KeyError:
        raise dacite.DaciteError(f"invalid follow_imports value: {s}") from None


def _parse_mypy_preset(s: Any) -> MypyPreset:
    if not isinstance(s, str):
        raise dacite.WrongTypeError(MypyPreset, s)

    try:
        return MypyPreset[s.upper()]
    except KeyError:
        raise dacite.DaciteError(f"invalid mypy_preset value: {s}") from None


def _parse_isort_section_name(s: Any) -> IsortSectionName:
    if not isinstance(s, str):
        raise dacite.WrongTypeError(MypyPreset, s)

    try:
        return IsortSectionName[s.upper()]
    except KeyError:
        raise dacite.DaciteError(f"invalid default_section value: {s}") from None


def _parse_python_version(s: Any) -> PythonVersion:
    if not isinstance(s, str):
        raise dacite.WrongTypeError(str, s)

    try:
        return PythonVersion.parse_short_representation(s)
    except KeyError as e:
        raise dacite.DaciteError(str(e))


def _expand_path(base_dir: pathlib.Path, s: Any) -> pathlib.Path:
    if isinstance(s, pathlib.Path):
        return s
    elif isinstance(s, str):
        return base_dir / s
    else:
        raise dacite.WrongTypeError(pathlib.Path, s)


def _parse_source(base_dir: pathlib.Path, d: Any) -> Source:
    if isinstance(d, list):
        return Source(includes=[_expand_path(base_dir, x) for x in d])
    elif isinstance(d, dict):

        @dataclasses.dataclass
        class _SourceConfig:
            includes: Optional[List[pathlib.Path]] = None
            include_globs: Optional[List[str]] = None
            excludes: Optional[List[pathlib.Path]] = None
            exclude_globs: Optional[List[str]] = None

        config = dacite.from_dict(
            _SourceConfig,
            d,
            config=dacite.Config(
                type_hooks={pathlib.Path: lambda x: _expand_path(base_dir, x)},
                strict=True,
            ),
        )
        source = Source(includes=config.includes, excludes=config.excludes)
        if config.include_globs is not None:
            for i in config.include_globs:
                source.add_include(i, glob=True, base_dir=base_dir)

        if config.exclude_globs is not None:
            for e in config.exclude_globs:
                source.add_exclude(e, glob=True, base_dir=base_dir)

        if len(source.includes) == 0:
            source.add_include(".", base_dir=base_dir)

        return source

    else:
        raise dacite.DaciteError(f"invalid source value: {d}") from None


def _parse_mypy_target(base_dir: pathlib.Path, d: Any) -> MypyTarget:
    if not isinstance(d, dict):
        raise dacite.WrongTypeError(dict, d, "tool.pysen.lint.mypy_targets")

    target = dacite.from_dict(
        MypyTarget,
        d,
        config=dacite.Config(
            type_hooks={pathlib.Path: lambda x: _expand_path(base_dir, x)},
            strict=True,
        ),
    )
    assert isinstance(target, MypyTarget)
    if len(target.paths) == 0:
        raise dacite.DaciteError(
            "invalid mypy_target: each target must have one or more paths"
        )

    return target


def _parse_mypy_targets(base_dir: pathlib.Path, config: Any) -> List[MypyTarget]:
    if not isinstance(config, list):
        raise dacite.WrongTypeError(List[MypyTarget], config)

    if not all(isinstance(x, dict) for x in config):
        raise dacite.DaciteError("tool.pysen.lint.mypy_targets must be a list of dicts")

    return [_parse_mypy_target(base_dir, x) for x in config]


def _parse_mypy_modules(config: Any) -> Dict[str, MypyModuleOption]:
    if not isinstance(config, dict):
        raise dacite.WrongTypeError(Dict[str, MypyModuleOption], config)

    mypy_modules: Dict[str, MypyModuleOption] = {}

    for target_module, option_dict in config.items():
        if not isinstance(target_module, str):
            raise dacite.WrongTypeError(
                str, target_module, "tool.pysen.lint.mypy_modules"
            )

        if not isinstance(option_dict, dict):
            raise dacite.WrongTypeError(
                MypyModuleOption,
                option_dict,
                f'tool.pysen.lint.mypy_modules."{target_module}"',
            )

        try:
            module_option = dacite.from_dict(
                MypyModuleOption,
                option_dict,
                config=dacite.Config(
                    strict=True,
                    type_hooks={
                        MypyPreset: _parse_mypy_preset,
                        MypyFollowImports: _parse_mypy_follow_imports,
                    },
                ),
            )
            assert isinstance(module_option, MypyModuleOption)
            mypy_modules[target_module] = module_option
        except ValueError as e:
            raise dacite.DaciteError(f"invalid mypy_module: {target_module}, {e}")

    return mypy_modules


def _parse_dict(data: Dict[str, Any], base_dir: pathlib.Path) -> Config:
    dacite_config = dacite.Config(
        type_hooks={
            MypyPreset: _parse_mypy_preset,
            IsortSectionName: _parse_isort_section_name,
            pathlib.Path: lambda x: _expand_path(base_dir, x),
            Source: lambda x: _parse_source(base_dir, x),
            List[PluginConfig]: lambda x: _parse_plugin_configs(base_dir, x),
            VersionRepresentation: VersionRepresentation.from_str,
            PythonVersion: _parse_python_version,
            List[MypyTarget]: lambda x: _parse_mypy_targets(base_dir, x),
            Dict[str, MypyModuleOption]: _parse_mypy_modules,
        },
        strict=True,
    )

    try:
        config = dacite.from_dict(Config, data, dacite_config)
        assert isinstance(config, Config)
        return config
    except dacite.DaciteError as e:
        raise InvalidConfigurationError(f"invalid configuration: {e}") from None


def _workaround_tomlkit_unmarshal(data: Any) -> Any:
    if data is None or isinstance(data, tomlkit.items.Null):
        return None
    elif isinstance(data, dict):
        # tomlkit.items.Dict, tomlkit.container.Container
        ret: Dict[str, Any] = {}
        for k, v in data.items():
            k = _workaround_tomlkit_unmarshal(k)
            v = _workaround_tomlkit_unmarshal(v)
            ret[k] = v

        return ret
    elif isinstance(data, list):
        # tomlkit.items.Array
        return list([_workaround_tomlkit_unmarshal(v) for v in data])
    elif isinstance(data, tomlkit.items.Bool):
        return bool(data)
    elif isinstance(data, tomlkit.items.Float):
        return float(data)
    elif isinstance(data, tomlkit.items.Integer):
        return int(data)
    elif isinstance(data, tomlkit.items.String):
        return str(data)
    elif isinstance(
        data, (tomlkit.items.DateTime, tomlkit.items.Date, tomlkit.items.Time)
    ):
        raise NotImplementedError(f"tomlkit type: {type(data)}")

    return data


def has_tool_section(
    tool_name: str,
    pyproject: tomlkit.toml_document.TOMLDocument,
) -> bool:
    return "tool" in pyproject and tool_name in pyproject["tool"]


def _load_pysen_section(path: pathlib.Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open("r") as f:
        pyproject = tomlkit.loads(f.read())

    if has_tool_section("pysen", pyproject):
        section = pyproject["tool"]["pysen"]
    elif has_tool_section("jiro", pyproject):
        _logger.warning(
            "jiro section under pyproject.toml is deprecated. Use pysen instead."
        )
        section = pyproject["tool"]["jiro"]
    else:
        raise PysenSectionNotFoundError(str(path))

    data = _workaround_tomlkit_unmarshal(section)
    assert isinstance(data, dict)
    return data


def _migrate_alias_fields(config: Config) -> None:
    if config.lint is not None:
        lint_config = config.lint

        if lint_config.mypy_ignore_packages is not None:
            mypy_modules: Dict[str, MypyModuleOption] = lint_config.mypy_modules or {}

            for m in lint_config.mypy_ignore_packages:
                if m in mypy_modules:
                    raise dacite.DaciteError(
                        f"{m} is configured in both mypy_ignore_packages and mypy_modules"
                    )

                mypy_modules[m] = MypyModuleOption(
                    ignore_errors=True, follow_imports=MypyFollowImports.SKIP
                )

            lint_config.mypy_ignore_packages = None
            lint_config.mypy_modules = mypy_modules


def _migrate_deprecated_fields(path: pathlib.Path, config: Config) -> None:
    if config.lint is not None:
        if config.lint.mypy_target_dirs is not None:
            _logger.warning(
                "tool.pysen.mypy_target_dirs is deprecated since 0.6.0, "
                f"Use tool.pysen.mypy_targets instead (File: {path})"
            )
            config.lint.mypy_targets = [MypyTarget(config.lint.mypy_target_dirs)]
            config.lint.mypy_target_dirs = None


def _load_version(data: Dict[str, Any]) -> Optional[VersionRepresentation]:
    version = data.get("version")
    if version is None:
        return None

    try:
        return VersionRepresentation.from_str(version)
    except ValueError as e:
        raise InvalidConfigurationError(e) from None


def _check_version(
    file_path: pathlib.Path,
    config_version: Optional[VersionRepresentation],
    actual_version: VersionRepresentation,
) -> None:
    if config_version is None:
        _logger.warning(
            "Consider specifying 'version' under [tool.pysen] section in your pyproject.toml "
            "to check compliance against the version of the installed pysen. "
            f"(File: {file_path})"
        )
    elif not config_version.is_compatible(actual_version):
        _logger.warning(
            f"pyproject.toml specifies version {config_version}, "
            f"but the pysen you are using is version {actual_version}, "
            "which might not be compatible. "
            f"(File: {file_path})"
        )


def parse(path: pathlib.Path) -> Config:
    path = path.resolve()
    base_dir = path.parent

    section = _load_pysen_section(path)
    version = _load_version(section)
    _check_version(path, version, VersionRepresentation.from_str(__version__))

    config = _parse_dict(section, base_dir)
    _migrate_alias_fields(config)
    _migrate_deprecated_fields(path, config)
    return config
