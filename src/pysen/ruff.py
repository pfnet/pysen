import pathlib
from dataclasses import dataclass
from typing import Any, DefaultDict, Dict, List, Optional, Sequence, Tuple

from pysen.command import CommandBase
from pysen.component import LintComponentBase
from pysen.ext import ruff_wrapper
from pysen.lint_command import LintCommandBase
from pysen.path import resolve_path
from pysen.reporter import Reporter
from pysen.source import PythonFileFilter, Source

from .flake8 import Flake8Setting
from .isort import IsortSetting
from .runner_options import PathContext, RunOptions
from .setting import SettingBase, SettingFile

_SettingFileName = "pyproject.toml"


@dataclass
class RuffSetting(SettingBase):
    line_length: int = 88
    select: Optional[List[str]] = None
    ignore: Optional[List[str]] = None
    known_first_party: Optional[List[str]] = None
    known_third_party: Optional[List[str]] = None

    @staticmethod
    def default() -> "RuffSetting":
        return RuffSetting()

    def export_top_level(self) -> Tuple[List[str], Dict[str, Any]]:
        section_name = ["tool", "ruff"]
        entries: Dict[str, Any] = {
            "line-length": self.line_length,
        }
        if self.select is not None:
            entries["select"] = self.select
        if self.ignore is not None:
            entries["ignore"] = self.ignore
        return section_name, entries

    def export_isort(self) -> Tuple[List[str], Dict[str, Any]]:
        section_name = ["tool", "ruff", "isort"]
        entries: Dict[str, Any] = {}
        if self.known_first_party is not None:
            entries["known-first-party"] = self.known_first_party
        if self.known_third_party is not None:
            entries["known-third-party"] = self.known_third_party
        return section_name, entries


class RuffCommand(LintCommandBase):
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
        return ruff_wrapper.run(
            reporter, self.base_dir, self._setting_path, sources, self._inplace_edit
        )

    def run_files(self, reporter: Reporter, files: Sequence[pathlib.Path]) -> int:
        covered_files = self._get_covered_files(reporter, files, PythonFileFilter)

        if len(covered_files) == 0:
            return 0

        return ruff_wrapper.run(
            reporter,
            self.base_dir,
            self._setting_path,
            files,
            self._inplace_edit,
        )


class Ruff(LintComponentBase):
    def __init__(
        self,
        name: str = "ruff",
        setting: Optional[RuffSetting] = None,
        source: Optional[Source] = None,
    ) -> None:
        super().__init__(name, source)
        self._setting = setting or RuffSetting.default()

    @property
    def setting(self) -> RuffSetting:
        return self._setting

    @setting.setter
    def setting(self, value: RuffSetting) -> None:
        self._setting = value

    def export_settings(
        self,
        paths: PathContext,
        files: DefaultDict[str, SettingFile],
    ) -> None:
        setting_file = files[_SettingFileName]
        setting_file.set_section(*self._setting.export_top_level())
        setting_file.set_section(*self._setting.export_isort())

    @property
    def targets(self) -> Sequence[str]:
        return ["lint", "format"]

    def create_command(
        self, target: str, paths: PathContext, options: RunOptions
    ) -> CommandBase:
        if target == "lint":
            return RuffCommand(self.name, paths, self.source, False)
        elif target == "format":
            return RuffCommand(self.name, paths, self.source, True)

        raise AssertionError(f"unknown {target}")
