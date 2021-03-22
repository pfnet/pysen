import pathlib
from typing import DefaultDict, Optional, Sequence

from pysen.ext import flake8_wrapper
from pysen.ext.flake8_wrapper import Flake8Setting

from .command import CommandBase
from .component import LintComponentBase
from .lint_command import LintCommandBase
from .path import resolve_path
from .reporter import Reporter
from .runner_options import PathContext, RunOptions
from .setting import SettingFile
from .source import PythonFileFilter, Source

_SettingFileName = "setup.cfg"


class Flake8Command(LintCommandBase):
    def __init__(self, name: str, paths: PathContext, source: Source) -> None:
        super().__init__(paths.base_dir, source)
        self._name = name
        self._setting_path = resolve_path(paths.settings_dir, _SettingFileName)

    @property
    def name(self) -> str:
        return self._name

    @property
    def has_side_effects(self) -> bool:
        return False

    def __call__(self, reporter: Reporter) -> int:
        sources = self._get_sources(reporter, PythonFileFilter)
        reporter.logger.info(f"Checking {len(sources)} files")
        return flake8_wrapper.run(reporter, self.base_dir, self._setting_path, sources)

    def run_files(self, reporter: Reporter, files: Sequence[pathlib.Path]) -> int:
        covered_files = self._get_covered_files(reporter, files, PythonFileFilter)

        if len(covered_files) == 0:
            return 0

        return flake8_wrapper.run(reporter, self.base_dir, self._setting_path, files)


class Flake8(LintComponentBase):
    def __init__(
        self,
        name: str = "flake8",
        setting: Optional[Flake8Setting] = None,
        source: Optional[Source] = None,
    ) -> None:
        super().__init__(name, source)
        self._setting = setting or Flake8Setting.default()

    @property
    def setting(self) -> Flake8Setting:
        return self._setting

    @setting.setter
    def setting(self, value: Flake8Setting) -> None:
        self._setting = value

    def export_settings(
        self,
        paths: PathContext,
        files: DefaultDict[str, SettingFile],
    ) -> None:
        setting_file = files[_SettingFileName]
        section, setting = self._setting.export()
        setting_file.set_section(section, setting)

    @property
    def targets(self) -> Sequence[str]:
        return ["lint"]

    def create_command(
        self, target: str, paths: PathContext, options: RunOptions
    ) -> CommandBase:
        if target == "lint":
            return Flake8Command(self.name, paths, self.source)

        raise AssertionError(f"unknown {target}")
