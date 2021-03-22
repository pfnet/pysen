import dataclasses
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


@dataclasses.dataclass
class Diagnostic:
    file_path: Path
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    start_column: Optional[int] = None
    message: Optional[str] = None
    diff: Optional[str] = None

    def __post_init__(self) -> None:
        assert self.file_path.is_absolute()
        if self.message is None and self.diff is None:
            raise ValueError("either message or diff must be filled")


class DiagnosticFormatter(ABC):
    @abstractmethod
    def format(self, diagnostic: Diagnostic, command_name: str) -> str:
        ...


def _format_diagnostic_position(diagnostic: Diagnostic) -> str:
    file_path = diagnostic.file_path.resolve()
    line = diagnostic.start_line or 1
    col = diagnostic.start_column or 1
    return f"{file_path}:{line}:{col}"


class _FLCMFormatter(DiagnosticFormatter):
    """
    FLCM: File, Line, Column, Message
    also see: https://www.gnu.org/prep/standards/html_node/Errors.html
    """

    def format(self, diagnostic: Diagnostic, command_name: str) -> str:
        position = _format_diagnostic_position(diagnostic)
        message: str
        if diagnostic.message:
            message = diagnostic.message.replace("\n", "\\n")
        elif diagnostic.diff:
            message = diagnostic.diff.replace("\n", "\\n")
        else:
            raise AssertionError()

        return f"{position}:{command_name}: {message}"


class _PrettyFormatter(DiagnosticFormatter):
    def format(self, diagnostic: Diagnostic, command_name: str) -> str:
        position = _format_diagnostic_position(diagnostic)
        message: str
        if diagnostic.message:
            message = diagnostic.message
        elif diagnostic.diff:
            message = f"\n{diagnostic.diff}"
        else:
            raise AssertionError()

        return f"[{command_name}] {position}:{message}"


FLCMFormatter = _FLCMFormatter()
PrettyFormatter = _PrettyFormatter()
