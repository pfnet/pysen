import logging
import pathlib
from typing import Callable, List, Optional, Sequence, Set, TypeVar

import tomlkit

from .component import ComponentBase
from .exceptions import InvalidConfigurationError
from .factory import configure_lint
from .manifest import ManifestBase
from .manifest_builder import build
from .mypy import Mypy
from .plugin_loader import load_plugin
from .pyproject_model import Config, LintConfig, has_tool_section, parse

_logger = logging.getLogger(__name__)
TConfig = TypeVar("TConfig")


def resolve_inheritance(
    path: pathlib.Path,
    selector: Callable[[pathlib.Path, Config], TConfig],
    base_selector: Callable[[pathlib.Path, TConfig], Optional[pathlib.Path]],
    updater: Callable[[TConfig, TConfig], TConfig],
    visited: Optional[Set[pathlib.Path]] = None,
) -> TConfig:
    visited = visited or set()
    if path in visited:
        raise InvalidConfigurationError(
            f"Circular dependency detected. {path} was visited more than once."
        )
    visited.add(path)

    config = parse(path)
    if config is None:
        raise InvalidConfigurationError(
            f"invalid base config: {path} doesn't exists or invalid file"
        )

    section = selector(path, config)
    base_path = base_selector(path, section)

    if base_path is None:
        return section

    base_section = resolve_inheritance(
        base_path, selector, base_selector, updater, visited
    )
    return updater(base_section, section)


def resolve_lint_config_inheritance(config: LintConfig) -> LintConfig:
    def selector(path: pathlib.Path, root: Config) -> LintConfig:
        if root.lint is None:
            raise InvalidConfigurationError(
                f"detected {path} doesn't have [tool.pysen.lint] section."
            )

        return root.lint

    def base_selector(path: pathlib.Path, c: LintConfig) -> Optional[pathlib.Path]:
        return c.base

    def updater(lhs: LintConfig, rhs: LintConfig) -> LintConfig:
        lhs.update(rhs)
        return lhs

    if config.base is None:
        return config

    base = resolve_inheritance(config.base, selector, base_selector, updater)
    base.update(config)
    return base


def load_lint_components(config: LintConfig) -> Sequence[ComponentBase]:
    config = resolve_lint_config_inheritance(config)
    components = configure_lint(config)

    # NOTE(igarashi): set convert_abspath=True to create a relative path from a absolute path
    if config.enable_mypy:
        mypy = next(c for c in components if isinstance(c, Mypy))
        mypy.setting._pysen_convert_abspath = True

        for _, s in mypy.module_settings.items():
            s._pysen_convert_abspath = True

    return components


def load_manifest(path: pathlib.Path) -> ManifestBase:
    config = parse(path)

    external_builder: Optional[pathlib.Path] = config.builder
    components: List[ComponentBase] = []

    if config.lint is not None:
        components.extend(load_lint_components(config.lint))

    if config.plugin is not None:
        for p in config.plugin:
            plugin = load_plugin(function=p.function, script=p.script)
            components.extend(plugin.load(path, p, config))

    return build(components, path, external_builder)


def _find_recursive() -> Optional[pathlib.Path]:
    current = pathlib.Path.cwd().resolve()

    while True:
        path = current / "pyproject.toml"
        if path.exists() and path.is_file():
            pyproject = tomlkit.loads(path.read_text())
            if has_tool_section("jiro", pyproject) or has_tool_section(
                "pysen", pyproject
            ):
                _logger.debug(f"successfully found pyproject.toml: {path}")
                return path

            _logger.debug(f"found a file, but pysen.tool doesn't exist: {path}")

        # reached root
        if current.parent == current:
            return None

        current = current.parent


def find_pyproject(path: Optional[pathlib.Path] = None) -> pathlib.Path:
    if path is not None:
        path = path.resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        elif not path.is_file():
            raise FileNotFoundError(f"{path} is not a file")

        return path
    else:
        p = _find_recursive()
        if p is None:
            raise FileNotFoundError(
                "Could not find a pyproject.toml file "
                "containing a [tool.pysen] section "
                "in this or any of its parent directories. \n"
                "The `--loglevel debug option` may help."
            )
        return p
