import argparse
import pathlib
from typing import Dict, List, Mapping, Optional, Sequence

from pysen.command import CommandBase
from pysen.manifest import (
    ComponentName,
    ManifestBase,
    ParserType,
    TargetName,
    TargetType,
)
from pysen.runner_options import PathContext, RunOptions


class FakeManifest(ManifestBase):
    def __init__(
        self,
        expected_base_dir: pathlib.Path,
        expected_settings_dir: Optional[pathlib.Path],
        num_required: bool,
        items: Mapping[str, Sequence[CommandBase]],
        special_item: Sequence[CommandBase],
    ) -> None:
        self._expected_base_dir = expected_base_dir
        self._expected_settings_dir = expected_settings_dir
        self._num_required = num_required
        self._items = {k: list(v) for k, v in items.items()}
        self._special_item = list(special_item)
        # for test assertions
        self._latest_args: Optional[argparse.Namespace] = None

    def configure_parser(self, parser: ParserType) -> None:
        parser.add_argument("--special", action="store_true")
        parser.add_argument("--num", type=int, default=0, required=self._num_required)

    def _targets(self, args: argparse.Namespace) -> Dict[str, TargetType]:
        ret: Dict[str, TargetType] = self._items.copy()
        if args.special:
            ret["special"] = self._special_item

        length = args.num
        if length > 0:
            for k in ret.keys():
                v = ret[k][:length]
                ret[k] = v

        return ret

    def export_settings(self, paths: PathContext, args: argparse.Namespace) -> None:
        assert paths.base_dir == self._expected_base_dir
        if self._expected_settings_dir is not None:
            assert paths.settings_dir == self._expected_settings_dir
        self._latest_args = args

    def get_targets(self, args: argparse.Namespace) -> Dict[str, List[ComponentName]]:
        targets = self._targets(args)
        return {name: [x.name for x in value] for name, value in targets.items()}

    def get_target(
        self,
        target: TargetName,
        paths: PathContext,
        options: RunOptions,
        args: argparse.Namespace,
    ) -> TargetType:
        assert paths.base_dir == self._expected_base_dir
        if self._expected_settings_dir is not None:
            assert paths.settings_dir == self._expected_settings_dir
        return self._targets(args)[target]

    @property
    def latest_args(self) -> Optional[argparse.Namespace]:
        return self._latest_args

    @property
    def clear_latest_args(self) -> None:
        self._latest_args = None
