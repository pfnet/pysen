import pathlib
from typing import Optional, Sequence

import pysen
from pysen import Source
from pysen.component import ComponentBase
from pysen.manifest import Manifest, ManifestBase


def build(
    components: Sequence[ComponentBase], src_path: Optional[pathlib.Path]
) -> ManifestBase:
    source = Source([".", "tests", "tools"])
    mypy = pysen.Mypy(
        setting=pysen.MypySetting.strict(),
        module_settings={  # per module setting
            "example_advanced_package.cmds.*": pysen.MypySetting.entry(),
            "example_advanced_package.tools.*": pysen.MypySetting(
                disallow_any_generics=False,
            ),
        },
        mypy_targets=[
            pysen.MypyTarget([pathlib.Path("."), pathlib.Path("tests")]),
            pysen.MypyTarget([pathlib.Path("tools")]),
        ],
    )
    flake8_setting = pysen.Flake8Setting(
        ignore=["W", "E"], select=["B", "C", "F"], max_complexity=10
    )
    flake8 = pysen.Flake8(setting=flake8_setting, source=source)

    return Manifest([mypy, flake8])
