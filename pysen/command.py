import pathlib
import subprocess
from abc import ABC, abstractmethod
from typing import Sequence

from .exceptions import CommandNotFoundError, RunTargetFileNotSupported
from .reporter import Reporter


class CommandBase(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def __call__(self, reporter: Reporter) -> int:
        ...

    @property
    def has_side_effects(self) -> bool:
        return True

    def run(self, reporter: Reporter) -> int:
        return self.__call__(reporter)

    def run_files(self, reporter: Reporter, files: Sequence[pathlib.Path]) -> int:
        raise RunTargetFileNotSupported(self.name)


def check_command_installed(*validation_command: str) -> None:
    err = CommandNotFoundError(
        f"The command `{' '.join(validation_command)}` failed."
        " Make sure it is installed."
    )
    try:
        retval = subprocess.call(
            validation_command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        # This will be raised when self.validation_command[0] does not exist.
        raise err
    if retval == 127:
        # In some cases (e.g. pyenv), FileNotFoundError is not raised.
        # Instead, we look at the return code to tell if the command could not be found.
        raise err
