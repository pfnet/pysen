import dataclasses
import pathlib
from typing import Dict, List, Optional

from .black import Black, BlackSetting
from .component import ComponentBase
from .flake8 import Flake8, Flake8Setting
from .isort import Isort, IsortSectionName, IsortSetting
from .mypy import (
    Mypy,
    MypyFollowImports,
    MypyPlugin,
    MypyPreset,
    MypySetting,
    MypyTarget,
)
from .py_version import PythonVersion
from .source import Source


@dataclasses.dataclass
class MypyModuleOption:
    preset: Optional[MypyPreset] = None
    ignore_errors: bool = False
    follow_imports: Optional[MypyFollowImports] = None

    def __post_init__(self) -> None:
        if self.preset is not None and self.ignore_errors:
            raise ValueError("cannot specify both preset and ignore_errors")

    def get_setting(self) -> MypySetting:
        if self.ignore_errors:
            return MypySetting(ignore_errors=True, follow_imports=self.follow_imports)

        preset: MypyPreset
        if self.preset is not None:
            preset = self.preset
        else:
            preset = MypyPreset.STRICT

        return preset.get_setting(follow_imports=self.follow_imports)


@dataclasses.dataclass
class ConfigureLintOptions:
    enable_black: Optional[bool] = None
    enable_flake8: Optional[bool] = None
    enable_isort: Optional[bool] = None
    enable_mypy: Optional[bool] = None
    mypy_preset: Optional[MypyPreset] = None
    mypy_modules: Optional[Dict[str, MypyModuleOption]] = None
    source: Optional[Source] = None
    line_length: Optional[int] = None
    py_version: Optional[PythonVersion] = None
    isort_known_third_party: Optional[List[str]] = None
    isort_known_first_party: Optional[List[str]] = None
    isort_default_section: Optional[IsortSectionName] = None
    mypy_path: Optional[List[pathlib.Path]] = None
    mypy_plugins: Optional[List[MypyPlugin]] = None
    mypy_targets: Optional[List[MypyTarget]] = None


def configure_lint(options: ConfigureLintOptions) -> List[ComponentBase]:
    components: List[ComponentBase] = []

    python_version: PythonVersion
    if options.py_version is not None:
        python_version = options.py_version
    else:
        python_version = PythonVersion(3, 7)

    line_length = options.line_length or 88

    # NOTE: `isort` may format code in a way that violates `black` rules
    # Apply `isort` after `black` to avoid such violation
    if options.enable_isort:
        isort_setting = IsortSetting.default()
        isort_setting.line_length = line_length
        isort_setting.default_section = (
            options.isort_default_section or IsortSectionName.THIRDPARTY
        )
        if options.isort_known_third_party is not None:
            isort_setting.known_third_party = set(options.isort_known_third_party)
        if options.isort_known_first_party is not None:
            isort_setting.known_first_party = set(options.isort_known_first_party)

        if options.enable_black:
            isort_setting = isort_setting.to_black_compatible()

        isort = Isort(setting=isort_setting, source=options.source)
        components.append(isort)

    if options.enable_black:
        black_setting = BlackSetting.default(python_version)
        black_setting.line_length = line_length
        black = Black(setting=black_setting, source=options.source)
        components.append(black)

    if options.enable_flake8:
        flake8_setting = Flake8Setting.default()
        flake8_setting.max_line_length = line_length
        if options.enable_black:
            flake8_setting = flake8_setting.to_black_compatible()

        flake8 = Flake8(setting=flake8_setting, source=options.source)
        components.append(flake8)

    if options.enable_mypy:
        if options.mypy_preset is not None:
            mypy_setting = options.mypy_preset.get_setting()
        else:
            mypy_setting = MypySetting.strict()
        mypy_setting.python_version = python_version
        if options.mypy_path is not None:
            mypy_setting.mypy_path = list(options.mypy_path)
        if options.mypy_plugins is not None:
            mypy_setting.plugins = list(options.mypy_plugins)

        mypy_module_settings: Dict[str, MypySetting] = {}
        if options.mypy_modules is not None:
            for module_name, module_option in options.mypy_modules.items():
                mypy_module_settings[module_name] = module_option.get_setting()

        mypy = Mypy(
            setting=mypy_setting,
            module_settings=mypy_module_settings,
            mypy_targets=options.mypy_targets,
        )
        components.append(mypy)

    return components
