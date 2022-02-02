import dataclasses
import pathlib
import subprocess
from typing import DefaultDict, List, Sequence

import dacite

from pysen.command import CommandBase
from pysen.component import ComponentBase, RunOptions
from pysen.path import change_dir
from pysen.plugin import PluginBase
from pysen.pyproject_model import Config, PluginConfig
from pysen.reporter import Reporter
from pysen.runner_options import PathContext
from pysen.setting import SettingFile


class ShellCommand(CommandBase):
    def __init__(self, name: str, base_dir: pathlib.Path, cmd: Sequence[str]) -> None:
        self._name = name
        self._base_dir = base_dir
        self._cmd = cmd

    @property
    def name(self) -> str:
        return self._name

    def __call__(self, reporter: Reporter) -> int:
        with change_dir(self._base_dir):
            try:
                ret = subprocess.run(self._cmd)
                reporter.logger.info(f"{self._cmd} returns {ret.returncode}")
                return ret.returncode
            except BaseException as e:
                reporter.logger.info(
                    f"an error occurred while executing: {self._cmd}\n{e}"
                )
                return 255


class ShellComponent(ComponentBase):
    def __init__(self, name: str, cmd: Sequence[str], targets: Sequence[str]) -> None:
        self._name = name
        self._cmd = cmd
        self._targets = targets

    @property
    def name(self) -> str:
        return self._name

    def export_settings(
        self, paths: PathContext, files: DefaultDict[str, SettingFile],
    ) -> None:
        print(f"Called export_settings at {self._name}: do nothing")

    @property
    def targets(self) -> Sequence[str]:
        return self._targets

    def create_command(
        self, target: str, paths: PathContext, options: RunOptions
    ) -> CommandBase:
        assert target in self._targets
        return ShellCommand(self._name, paths.base_dir, self._cmd)


@dataclasses.dataclass
class ShellPluginConfig:
    name: str
    command: List[str]
    targets: List[str]


class ShellPlugin(PluginBase):
    def load(
        self, file_path: pathlib.Path, config_data: PluginConfig, root: Config
    ) -> Sequence[ComponentBase]:
        assert (
            config_data.config is not None
        ), f"{config_data.location}.config must be not None"
        config = dacite.from_dict(
            ShellPluginConfig, config_data.config, dacite.Config(strict=True)
        )
        return [ShellComponent(config.name, config.command, config.targets)]


# NOTE(igarashi): This is the entry point of a plugin method
def plugin() -> PluginBase:
    return ShellPlugin()
