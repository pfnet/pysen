from abc import ABC, abstractmethod
from typing import DefaultDict, Optional, Sequence

from .command import CommandBase
from .runner_options import PathContext, RunOptions
from .setting import SettingFile
from .source import Source
from .types import ComponentName, TargetName


class ComponentBase(ABC):
    @property
    def name(self) -> Optional[ComponentName]:
        return None

    def export_settings(
        self,
        paths: PathContext,
        files: DefaultDict[str, SettingFile],
    ) -> None:
        pass

    @property
    @abstractmethod
    def targets(self) -> Sequence[TargetName]:
        ...

    @abstractmethod
    def create_command(
        self, target: str, paths: PathContext, options: RunOptions
    ) -> CommandBase:
        ...


class LintComponentBase(ComponentBase):
    def __init__(self, name: str, source: Optional[Source] = None) -> None:
        self._name = name
        self._source: Source = source or Source(includes=["."])

    @property
    def name(self) -> ComponentName:
        return self._name

    @property
    def source(self) -> Source:
        return self._source

    @source.setter
    def source(self, value: Source) -> None:
        self._source = value
