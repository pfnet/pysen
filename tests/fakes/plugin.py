import dataclasses
import pathlib
from typing import List, Sequence

import dacite

from fakes.component import FakeComponent, Operation
from pysen.component import ComponentBase
from pysen.plugin import PluginBase
from pysen.pyproject_model import Config, PluginConfig


@dataclasses.dataclass
class FakePluginConfig:
    enable_c1: bool = False
    enable_c2: bool = False


class FakePlugin(PluginBase):
    def __init__(self, name: str) -> None:
        self._name = name

    def load(
        self, file_path: pathlib.Path, config_data: PluginConfig, root: Config
    ) -> Sequence[ComponentBase]:
        config = FakePluginConfig()
        if config_data.config is not None:
            config = dacite.from_dict(
                FakePluginConfig, config_data.config, dacite.Config(strict=True)
            )

        r = [0.0]
        components: List[ComponentBase] = []

        if config.enable_c1:
            components.append(
                FakeComponent(
                    f"{self._name}_component1",
                    {"op1": (2, Operation.MUL), "op2": (10, Operation.ADD)},
                    None,
                    None,
                    r,
                )
            )

        if config.enable_c2:
            components.append(
                FakeComponent(
                    f"{self._name}_component2",
                    {"op1": (3, Operation.MUL), "op3": (-1, Operation.MUL)},
                    None,
                    None,
                    r,
                )
            )

        return components


def create() -> PluginBase:
    return FakePlugin("create")


def plugin() -> PluginBase:
    return FakePlugin("plugin")
