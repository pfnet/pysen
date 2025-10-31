import argparse
import collections
import dataclasses
import pathlib
from abc import ABC, abstractmethod
from typing import Callable, DefaultDict, Dict, Iterable, List, Optional, Sequence

from .command import CommandBase
from .component import ComponentBase
from .dumper import dump
from .exceptions import InvalidComponentName
from .runner_options import PathContext, RunOptions
from .setting import SettingFile
from .types import ComponentName, TargetName

DumpHandlerType = Callable[
    [pathlib.Path, str, SettingFile],
    None,
]

ParserType = argparse._ActionsContainer
TargetType = List[CommandBase]


def get_targets(
    components: Sequence[ComponentBase],
) -> Dict[TargetName, List[ComponentName]]:
    result: DefaultDict[str, List[ComponentName]] = collections.defaultdict(list)
    for c in components:
        targets = c.targets
        for t in targets:
            result[t].append(c.name or "(no name)")

    return dict(result)


def get_target(
    target: TargetName,
    components: Sequence[ComponentBase],
    paths: PathContext,
    options: RunOptions,
) -> TargetType:
    result: TargetType = []
    for c in components:
        targets = c.targets
        if target in targets:
            result.append(c.create_command(target, paths, options))

    return result


def export_settings(
    paths: PathContext,
    components: Sequence[ComponentBase],
    dump_handler: DumpHandlerType,
) -> None:
    files: DefaultDict[str, SettingFile] = collections.defaultdict(SettingFile)
    for c in components:
        c.export_settings(paths, files)

    for fname, setting in files.items():
        try:
            dump_handler(
                paths.settings_dir,
                fname,
                setting,
            )
        except Exception as err:
            raise RuntimeError(f"got an unexpected error while creating {fname}: {err}")


class ManifestBase(ABC):
    def configure_parser(self, parser: ParserType) -> None:
        pass

    @abstractmethod
    def export_settings(self, paths: PathContext, args: argparse.Namespace) -> None:
        ...

    @abstractmethod
    def get_targets(
        self, args: argparse.Namespace
    ) -> Dict[TargetName, List[ComponentName]]:
        ...

    @abstractmethod
    def get_target(
        self,
        target: TargetName,
        paths: PathContext,
        options: RunOptions,
        args: argparse.Namespace,
    ) -> TargetType:
        ...


@dataclasses.dataclass(frozen=True)
class ManifestOptions:
    enabled: Optional[List[str]]
    disabled: Optional[List[str]]

    @staticmethod
    def configure_parser(parser: ParserType) -> None:
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--enable", action="append", help="component names to enable"
        )
        group.add_argument(
            "--disable", action="append", help="component names to disable"
        )

    @classmethod
    def from_parsed_arguments(cls, args: argparse.Namespace) -> "ManifestOptions":
        return cls(enabled=args.enable, disabled=args.disable)


def _verify_names(
    components: List[ComponentBase], names: List[str], option: str
) -> None:
    diff = set(names).difference(component.name for component in components)
    if diff:
        diff_str = ",".join(sorted(diff))
        raise InvalidComponentName(
            f"The following component(s) in option {option} were not found: {diff_str}"
        )


class Manifest(ManifestBase):
    def __init__(
        self,
        components: Optional[Sequence[ComponentBase]] = None,
        dump_handler: Optional[DumpHandlerType] = None,
    ) -> None:
        self._components: List[ComponentBase] = []
        if components is not None:
            self._components = list(components)

        self._dump_handler: DumpHandlerType = dump_handler or dump

    def configure_parser(self, parser: ParserType) -> None:
        ManifestOptions.configure_parser(parser)

    @property
    def components(self) -> List[ComponentBase]:
        return self._components

    def get_component(self, name: str) -> ComponentBase:
        for c in self._components:
            if c.name == name:
                return c
        else:
            raise KeyError(name)

    def _filter_components(self, args: argparse.Namespace) -> Iterable[ComponentBase]:
        options = ManifestOptions.from_parsed_arguments(args)
        enable = options.enabled
        disable = options.disabled

        if enable is None and disable is None:
            yield from self._components
            return

        predicate: Callable[[ComponentBase], bool]
        if enable is not None:
            _verify_names(self._components, enable, "--enable")

            def enable_predicate(x: ComponentBase) -> bool:
                assert enable is not None
                if x.name is None:
                    return False
                return x.name in enable

            predicate = enable_predicate
        elif disable is not None:
            _verify_names(self._components, disable, "--disable")

            def disable_predicate(x: ComponentBase) -> bool:
                assert disable is not None
                if x.name is None:
                    return True
                return x.name not in disable

            predicate = disable_predicate
        else:
            # NOTE(igarashi): `enable` and `disable` are in a mutually exclusive group
            raise AssertionError()

        for x in self._components:
            if predicate(x):
                yield x

    def export_settings(self, paths: PathContext, args: argparse.Namespace) -> None:
        # NOTE(igarashi): tomlkit doesn't keep the comments in the original file.
        # It will cause unnecessary changes when pysen doesn't export all configurations
        # since some comments like "automatically generated by pysen" would be partially removed
        # Therefore, ignore given args (`--disable` and `--enable`) as a workaround.
        export_settings(paths, self._components, self._dump_handler)

    def get_targets(
        self, args: argparse.Namespace
    ) -> Dict[TargetName, List[ComponentName]]:
        components = list(self._filter_components(args))
        return get_targets(components)

    def get_target(
        self,
        target: TargetName,
        paths: PathContext,
        options: RunOptions,
        args: argparse.Namespace,
    ) -> TargetType:
        components = list(self._filter_components(args))
        return get_target(target, components, paths, options)
