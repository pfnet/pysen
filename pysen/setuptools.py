import argparse
import functools
import pathlib
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Type, Union

import setuptools

from .manifest import ManifestBase
from .path import PathLikeType, wrap_path
from .pyproject import find_pyproject, load_manifest
from .reporter import ReporterFactory
from .runner import Runner
from .runner_options import RunOptions

ManifestLikeType = Union[str, pathlib.Path, ManifestBase]
CommandClassType = Type[setuptools.Command]
UNDEFINED = object()

_PREDEFINED_COMMAND_NAMES = [
    "build_ext",
    "build_py",
    "develop",
    "install",
    "test",
]


def _get_setuptool_command(name: str) -> CommandClassType:
    if name in _PREDEFINED_COMMAND_NAMES:
        try:
            import importlib

            module = importlib.import_module("setuptools.command.{}".format(name))
            klass = getattr(module, name)
            if (
                klass is not None
                and isinstance(klass, type)
                and issubclass(klass, setuptools.Command)
            ):
                return klass
        except BaseException:
            pass  # failover

    return setuptools.Command  # type: ignore


def _get_setuptool_user_options(
    klass: CommandClassType,
) -> List[Tuple[str, Optional[str], str]]:
    try:
        base_user_options = getattr(klass, "user_options", None)
        if base_user_options is not None and isinstance(
            base_user_options, (list, tuple)
        ):
            return list(base_user_options)
    except BaseException:
        pass  # failover

    return []


def _create_setuptool_command(
    name: str,
    runner: Runner,
    base_dir: pathlib.Path,
    settings_dir: Optional[pathlib.Path],
    manifest_args: argparse.Namespace,
) -> CommandClassType:
    base_class = _get_setuptool_command(name)
    base_user_options = _get_setuptool_user_options(base_class)

    setup_options = base_user_options

    class Cmd(base_class):  # type: ignore[valid-type,misc]  # NOQA: F821
        user_options = setup_options

        def __invoke_super(self, func: Callable[[], None]) -> None:
            if base_class is not setuptools.Command:
                func()

        def initialize_options(self) -> None:
            self.__invoke_super(super().initialize_options)

        def finalize_options(self) -> None:
            self.__invoke_super(super().finalize_options)

        def run(self) -> None:
            reporters = ReporterFactory()
            options = RunOptions()
            runner.run(
                name,
                base_dir,
                manifest_args,
                reporters,
                options,
                settings_dir=settings_dir,
                files=None,
            )
            print("\n ** execution summary **")
            print(reporters.format_summary())
            if reporters.has_error():
                sys.stderr.write(f"{name} finished with error(s)\n")
                print(reporters.format_error_summary())
                sys.exit(1)

            self.__invoke_super(super().run)

    Cmd.__name__ = name
    return Cmd


class SetupPyWrapper:
    def __init__(self, cmds: Dict[str, CommandClassType]) -> None:
        self._cmds = cmds

    @property
    def cmdclass(self) -> Dict[str, CommandClassType]:
        return self._cmds

    @functools.wraps(setuptools.setup)
    def __call__(self, **kwargs: Any) -> None:
        cmdclass = kwargs.pop("cmdclass", {})
        assert isinstance(cmdclass, dict)
        configured_cmds = self.cmdclass
        # NOTE(igarashi): raise Exception if the key is duplicated
        for key in cmdclass.keys():
            if key in configured_cmds:
                raise RuntimeError(f"cmdclass: {key} is duplicated")

        cmdclass.update(configured_cmds)
        kwargs.update({"cmdclass": cmdclass})

        setuptools.setup(**kwargs)


def _setup(
    package_dir: pathlib.Path,
    settings_dir: Optional[pathlib.Path],
    manifest: ManifestBase,
    args: Sequence[str],
) -> SetupPyWrapper:
    runner = Runner(manifest)
    parsed = runner.parse_manifest_arguments(args)
    targets = runner.get_targets(parsed)
    setup_commands = {
        name: _create_setuptool_command(name, runner, package_dir, settings_dir, parsed)
        for name in targets
    }

    return SetupPyWrapper(setup_commands)


def setup_from_pyproject(
    fpath: str,
    path: Optional[PathLikeType] = None,
    manifest_args: Optional[Sequence[str]] = None,
    settings_dir: Optional[pathlib.Path] = None,
) -> SetupPyWrapper:
    package_dir = pathlib.Path(fpath).resolve().parent
    wrapped: pathlib.Path = package_dir / "pyproject.toml"
    if path is not None:
        wrapped = wrap_path(path)

    args = manifest_args or []
    pyproject = find_pyproject(wrapped)
    manifest = load_manifest(pyproject)

    return _setup(package_dir, settings_dir, manifest, args)


def setup(
    fpath: str,
    manifest: ManifestBase,
    manifest_args: Optional[Sequence[str]] = None,
    settings_dir: Optional[pathlib.Path] = None,
) -> SetupPyWrapper:
    package_dir = pathlib.Path(fpath).resolve().parent
    args = manifest_args or []

    return _setup(package_dir, settings_dir, manifest, args)


def generate_setting_files(
    fpath: str,
    manifest: ManifestBase,
    export_dir: pathlib.Path,
    manifest_args: Optional[Sequence[str]] = None,
) -> None:
    package_dir = pathlib.Path(fpath).resolve().parent
    args = manifest_args or []
    runner = Runner(manifest)
    parsed = runner.parse_manifest_arguments(args)
    runner.export_settings(package_dir, export_dir, parsed)
