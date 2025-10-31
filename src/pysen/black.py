import pathlib
from typing import DefaultDict, Optional, Sequence

from pysen.ext import black_wrapper
from pysen.ext.black_wrapper import BlackSetting

from .command import CommandBase
from .component import LintComponentBase
from .lint_command import LintCommandBase
from .path import resolve_path
from .reporter import Reporter
from .runner_options import PathContext, RunOptions
from .setting import SettingFile
from .source import PythonFileFilter, Source

_SettingFileName = "pyproject.toml"


class BlackCommand(LintCommandBase):
    def __init__(
        self,
        name: str,
        paths: PathContext,
        source: Source,
        inplace_edit: bool,
    ) -> None:
        super().__init__(paths.base_dir, source)
        self._name = name
        self._setting_path = resolve_path(paths.settings_dir, _SettingFileName)
        self._inplace_edit = inplace_edit

    @property
    def name(self) -> str:
        return self._name

    @property
    def has_side_effects(self) -> bool:
        return self._inplace_edit

    def __call__(self, reporter: Reporter) -> int:
        sources = self._get_sources(reporter, PythonFileFilter)
        reporter.logger.info(f"Checking {len(sources)} files")
        return black_wrapper.run(
            reporter, self.base_dir, self._setting_path, sources, self._inplace_edit
        )

    def run_files(self, reporter: Reporter, files: Sequence[pathlib.Path]) -> int:
        covered_files = self._get_covered_files(reporter, files, PythonFileFilter)

        if len(covered_files) == 0:
            return 0

        return black_wrapper.run(
            reporter,
            self.base_dir,
            self._setting_path,
            covered_files,
            self._inplace_edit,
        )


class Black(LintComponentBase):
    def __init__(
        self,
        name: str = "black",
        setting: Optional[BlackSetting] = None,
        source: Optional[Source] = None,
    ) -> None:
        super().__init__(name, source)

        self._setting = setting or BlackSetting.default()

    @property
    def setting(self) -> BlackSetting:
        return self._setting

    @setting.setter
    def setting(self, value: BlackSetting) -> None:
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
        return ["lint", "format"]

    def create_command(
        self, target: str, paths: PathContext, options: RunOptions
    ) -> CommandBase:
        if target == "lint":
            return BlackCommand(self.name, paths, self.source, False)
        elif target == "format":
            return BlackCommand(self.name, paths, self.source, True)

        raise AssertionError(f"unknown {target}")
