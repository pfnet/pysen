import pathlib
from abc import ABC, abstractmethod
from typing import Sequence

from .component import ComponentBase
from .pyproject_model import Config, PluginConfig


class PluginBase(ABC):
    @abstractmethod
    def load(
        self, file_path: pathlib.Path, config: PluginConfig, root: Config
    ) -> Sequence[ComponentBase]:
        ...
