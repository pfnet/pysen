import dataclasses
import pathlib
from typing import Any, Dict, Optional

import dacite
import tomlkit

from .exceptions import InvalidConfigurationError
from .pyproject_model import _workaround_tomlkit_unmarshal


@dataclasses.dataclass
class CliConfig:
    settings_dir: Optional[pathlib.Path] = None


def _expand_path(base_dir: pathlib.Path, s: Any) -> pathlib.Path:
    if isinstance(s, pathlib.Path):
        return s
    elif isinstance(s, str):
        return base_dir / s
    else:
        raise dacite.WrongTypeError(pathlib.Path, s)


def _load_cli_section(path: pathlib.Path) -> Optional[Dict[str, Any]]:
    with path.open("r") as f:
        pyproject = tomlkit.loads(f.read())

    if "tool" not in pyproject or "pysen-cli" not in pyproject["tool"]:
        return None

    section = pyproject["tool"]["pysen-cli"]

    data = _workaround_tomlkit_unmarshal(section)
    assert isinstance(data, dict)
    return data


def _parse_dict(data: Dict[str, Any], base_dir: pathlib.Path) -> CliConfig:
    dacite_config = dacite.Config(
        type_hooks={pathlib.Path: lambda x: _expand_path(base_dir, x)},
        strict=True,
    )

    try:
        config = dacite.from_dict(CliConfig, data, dacite_config)
        assert isinstance(config, CliConfig)
        return config
    except dacite.DaciteError as e:
        raise InvalidConfigurationError(f"invalid configuration: {e}") from None


def parse(path: pathlib.Path) -> Optional[CliConfig]:
    base_dir = path.resolve().parent
    section = _load_cli_section(path)
    if section is None:
        return None
    return _parse_dict(section, base_dir)
