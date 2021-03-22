import contextlib
import io
import logging
import threading
import time
from typing import Any, Iterator, List, Optional, Sequence

from .diagnostic import Diagnostic, DiagnosticFormatter
from .logging_utils import (
    CommandLoggingOptions,
    get_process_output_logger,
    get_reporter_logger,
)

_COMMAND_REPR_MAX_LENGTH = 150
_OMIT_REPR = "..."


def _truncate_command_sequence(cmds: str) -> str:
    if len(cmds) <= _COMMAND_REPR_MAX_LENGTH:
        return cmds

    prefix_length = _COMMAND_REPR_MAX_LENGTH - len(_OMIT_REPR)
    assert prefix_length > 0
    prefix = cmds[:prefix_length]
    return f"{prefix}{_OMIT_REPR}"


class Reporter:
    def __init__(self, name: str) -> None:
        self._name = name
        self._success: Optional[bool] = None
        self._exit_code: Optional[int] = None

        self._commands: List[str] = []
        self._diagnostics: List[Diagnostic] = []
        self._started: Optional[float] = None
        self._ended: Optional[float] = None

        self._logger = get_reporter_logger(name)
        self._process_output = get_process_output_logger(name)

    @property
    def name(self) -> str:
        return self._name

    @property
    def success(self) -> bool:
        assert self._success is not None
        return self._success

    @property
    def exit_code(self) -> int:
        assert self._exit_code is not None
        return self._exit_code

    @property
    def commands(self) -> List[str]:
        assert self._commands is not None
        return self._commands

    @property
    def elapsed_time(self) -> float:
        assert self._started is not None
        assert self._ended is not None
        return self._ended - self._started

    @property
    def diagnostics(self) -> List[Diagnostic]:
        return self._diagnostics

    def __enter__(self) -> "Reporter":
        self._started = time.time()
        self.logger.info(f"Running: {self.name}")
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self._ended = time.time()

    def report_diagnostics(self, diagnostics: Sequence[Diagnostic]) -> None:
        self._diagnostics.extend(diagnostics)

    def report_command(self, cmd: str) -> None:
        self._logger.debug(f"> {_truncate_command_sequence(cmd)}")
        self._commands.append(cmd)

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def process_output(self) -> logging.Logger:
        return self._process_output

    def set_result(self, success: bool, exit_code: Optional[int] = None) -> None:
        self._success = success
        self._exit_code = exit_code


class ReporterFactory:
    def __init__(
        self,
        pretty: bool = True,
        process_output: bool = True,
        loglevel: int = logging.INFO,
    ) -> None:
        self._reporters: List[Reporter] = []
        self._lock = threading.Lock()
        self._pretty = pretty
        self._process_output = process_output
        self._loglevel = loglevel

    def create(self, name: str) -> Reporter:
        r = Reporter(name)
        with self._lock:
            self._reporters.append(r)
        return r

    @contextlib.contextmanager
    def logging_handlers(self, is_grouped: bool) -> Iterator[None]:
        clo = CommandLoggingOptions(is_grouped, self._pretty, self._process_output)
        with clo.start_logging(self._loglevel):
            yield

    def has_error(self) -> bool:
        return not all([r.success for r in self._reporters])

    @property
    def reporters(self) -> List[Reporter]:
        return self._reporters

    def format_summary(self) -> str:
        with io.StringIO() as buf:
            for r in self._reporters:
                status_msg = "Failed"
                if r.success:
                    status_msg = "OK"

                buf.write(
                    "{} .......... {} ({:.2f} sec)\n".format(
                        r.name, status_msg, r.elapsed_time
                    )
                )

            return buf.getvalue()

    def format_error_summary(self) -> str:
        with io.StringIO() as buf:
            buf.write("Errored:\n")
            for r in self._reporters:
                if not r.success:
                    buf.write(" - {}\n".format(r.name))
            return buf.getvalue()

    def format_diagnostic_summary(self, formatter: DiagnosticFormatter) -> str:
        ret: List[str] = []
        for r in self._reporters:
            for d in r.diagnostics:
                ret.append(formatter.format(d, r.name))

        return "\n".join(ret)
