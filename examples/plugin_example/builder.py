import argparse
import pathlib
from typing import Dict, List, Optional, Sequence

from pysen import dumper
from pysen.component import ComponentBase, LintComponentBase
from pysen.manifest import (
    ComponentName,
    ManifestBase,
    ParserType,
    TargetName,
    TargetType,
    export_settings,
    get_target,
    get_targets,
)
from pysen.runner_options import PathContext, RunOptions


class CustomManifest(ManifestBase):
    def __init__(self, components: Sequence[ComponentBase]) -> None:
        self._components = components

    def configure_parser(self, parser: ParserType) -> None:
        super().configure_parser(parser)

        parser.add_argument(
            "--ignore-lint",
            action="store_true",
            help="set True to ignore lint components",
        )

    def _get_components(self, args: argparse.Namespace) -> Sequence[ComponentBase]:
        components = self._components
        if args.ignore_lint:
            components = [c for c in components if not isinstance(c, LintComponentBase)]
        return components

    def export_settings(self, paths: PathContext, args: argparse.Namespace) -> None:
        export_settings(paths, self._components, dumper.dump)

    def get_targets(self, args: argparse.Namespace) -> Dict[str, List[ComponentName]]:
        return get_targets(self._get_components(args))

    def get_target(
        self,
        target: TargetName,
        paths: PathContext,
        options: RunOptions,
        args: argparse.Namespace,
    ) -> TargetType:
        return get_target(target, self._get_components(args), paths, options)


def build(
    components: Sequence[ComponentBase], src_path: Optional[pathlib.Path]
) -> ManifestBase:
    return CustomManifest(components)
