import itertools
import pathlib
from enum import Enum
from typing import Any, Callable, DefaultDict, Dict, List, Mapping, Optional, Sequence

from .command import CommandBase
from .component import ComponentBase
from .ext import mypy_wrapper
from .ext.mypy_wrapper import (  # NOQA
    MypyFollowImports,
    MypyPlugin,
    MypySetting,
    MypyTarget,
)
from .path import is_covered, resolve_path
from .reporter import Reporter
from .runner_options import PathContext, RunOptions
from .setting import SettingFile

_SettingFileName = "setup.cfg"


def _get_differences_from_base(
    entries: Dict[str, Any], base_entries: Dict[str, Any]
) -> Dict[str, Any]:
    # NOTE(igarashi): do not use `dict(entries.items() - base_entries.items())`
    # since entries may contain an unhashable type like lists.
    added = entries.keys() - base_entries.keys()
    duplicated = entries.keys() & base_entries.keys()

    diff: Dict[str, Any] = {}

    for key in added:
        diff[key] = entries[key]

    for key in duplicated:
        if entries[key] == base_entries[key]:
            continue

        diff[key] = entries[key]

    # NOTE(igarashi): Since there is no way to obtain a default value for each removed item,
    # we cannot put them to diff.
    # TODO(igarashi): Implement field attribute to each MypySetting option so that
    # we can get a default value. Uncomment the following code:
    # _IgnoreDifferenceFields = {"_pysen_convert_abspath", "python_version", "mypy_path"}
    # removed = base_entries.keys() - entries.keys() - _IgnoreDifferenceFields

    return diff


class MypyPreset(Enum):
    VERY_STRICT = (MypySetting.very_strict,)
    STRICT = (MypySetting.strict,)
    ENTRY = (MypySetting.entry,)

    def __init__(self, factory: Callable[..., MypySetting]) -> None:
        self._factory = factory

    def get_setting(self, **kwargs: Any) -> MypySetting:
        return self._factory(**kwargs)


class MypyCommand(CommandBase):
    def __init__(
        self,
        name: str,
        paths: PathContext,
        mypy_targets: Sequence[MypyTarget],
        require_diagnostics: bool,
    ) -> None:
        self._name = name
        self._base_dir = paths.base_dir
        self._mypy_targets: List[MypyTarget] = list(mypy_targets)

        self._setting_path = resolve_path(paths.settings_dir, _SettingFileName)
        self._require_diagnostics = require_diagnostics

    @property
    def name(self) -> str:
        return self._name

    @property
    def has_side_effects(self) -> bool:
        return False

    @property
    def base_dir(self) -> pathlib.Path:
        return self._base_dir

    @property
    def setting_path(self) -> pathlib.Path:
        return self._setting_path

    def __call__(self, reporter: Reporter) -> int:
        exit_code: int = 0
        num_targets = len(self._mypy_targets)

        if num_targets == 0:
            reporter.logger.error(
                "No mypy targets specified. "
                "You must specify at least one entry in `tools.pysen.lint.mypy_targets`."
            )
            return 2

        for idx, target in enumerate(self._mypy_targets):
            reporter.logger.info(
                f"[{idx+1}/{num_targets}] Checking {len(target.paths)} entries"
            )
            ret = mypy_wrapper.run(
                reporter,
                self.base_dir,
                self.setting_path,
                target,
                self._require_diagnostics,
            )
            if ret != 0:
                exit_code = ret

        return exit_code

    def run_files(self, reporter: Reporter, files: Sequence[pathlib.Path]) -> int:
        sources = list(
            itertools.chain.from_iterable(target.paths for target in self._mypy_targets)
        )
        covered_files: List[pathlib.Path] = []
        for f in files:
            if is_covered(f, sources):
                covered_files.append(f)
            else:
                reporter.logger.info(f"Skipping {f} for {self._name}")

        if len(covered_files) == 0:
            return 0

        return mypy_wrapper.run(
            reporter,
            self.base_dir,
            self._setting_path,
            MypyTarget(covered_files),
            self._require_diagnostics,
        )


class Mypy(ComponentBase):
    def __init__(
        self,
        name: str = "mypy",
        mypy_targets: Optional[Sequence[MypyTarget]] = None,
        setting: Optional[MypySetting] = None,
        module_settings: Optional[Mapping[str, MypySetting]] = None,
    ) -> None:
        self._name = name
        self._mypy_targets = list(mypy_targets or [])
        self._setting: MypySetting = setting or MypySetting()
        self._module_settings: Dict[str, MypySetting] = dict(module_settings or {})

    @property
    def name(self) -> str:
        return self._name

    @property
    def setting(self) -> MypySetting:
        return self._setting

    @property
    def module_settings(self) -> Dict[str, MypySetting]:
        return self._module_settings

    @property
    def mypy_targets(self) -> List[MypyTarget]:
        return self._mypy_targets

    def export_settings(
        self,
        paths: PathContext,
        files: DefaultDict[str, SettingFile],
    ) -> None:
        setting_file = files[_SettingFileName]
        global_section, global_setting = self._setting.export(paths.base_dir)
        setting_file.set_section(global_section, global_setting)

        for module_name, setting in self._module_settings.items():
            section, module_setting = setting.export(
                paths.base_dir, target_module=module_name
            )
            module_setting = _get_differences_from_base(module_setting, global_setting)
            setting_file.set_section(section, module_setting)

    @property
    def targets(self) -> Sequence[str]:
        return ["lint"]

    def create_command(
        self, target: str, paths: PathContext, options: RunOptions
    ) -> CommandBase:
        if target == "lint":
            return MypyCommand(
                self.name, paths, self.mypy_targets, options.require_diagnostics
            )

        raise AssertionError(f"unknown {target}")
