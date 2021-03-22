import collections
import contextlib
import dataclasses
import logging
import logging.handlers
from typing import DefaultDict, Iterator, List, Optional, cast

import colorlog
from colorlog import ColoredFormatter

_PROCESS_STDOUT_LEVEL = 11
_PROCESS_STDOUT = "STDOUT"
_PROCESS_STDERR_LEVEL = 12
_PROCESS_STDERR = "STDERR"

logging.addLevelName(_PROCESS_STDOUT_LEVEL, _PROCESS_STDOUT)
logging.addLevelName(_PROCESS_STDERR_LEVEL, _PROCESS_STDERR)


def _concat_logging_path(lhs: str, rhs: str) -> str:
    return f"{lhs}.{rhs}"


PYSEN_LOGGER_PREFIX = "__PYSEN__"
REPORTER_LOGGER_PREFIX = _concat_logging_path(PYSEN_LOGGER_PREFIX, "reporter")
PROCESS_OUTPUT_LOGGER_PREFIX = _concat_logging_path(PYSEN_LOGGER_PREFIX, "proc")

pysen_root_logger = logging.getLogger(PYSEN_LOGGER_PREFIX)
pysen_root_logger.propagate = False

reporter_root_logger = logging.getLogger(REPORTER_LOGGER_PREFIX)
reporter_root_logger.setLevel(logging.CRITICAL)

process_output_root_logger = logging.getLogger(PROCESS_OUTPUT_LOGGER_PREFIX)
process_output_root_logger.setLevel(logging.INFO)
# NOTE(igarashi): Set NullHandler() so that process_output_root_logger does not call
# the lastResort logger when propagate = False.
# See: https://github.com/python/cpython/blob/c3dd7e45cc5d36bbe2295c2840faabb5c75d83e4/Lib/logging/__init__.py#L1672-L1679  # NOQA
process_output_root_logger.addHandler(logging.NullHandler())
process_output_root_logger.propagate = False

_logging_output_colors = {
    **colorlog.default_log_colors,
    **{_PROCESS_STDOUT: "", _PROCESS_STDERR: "yellow"},
}


def get_reporter_logger(name: str) -> logging.Logger:
    return logging.getLogger(_concat_logging_path(REPORTER_LOGGER_PREFIX, name))


def get_process_output_logger(name: str) -> logging.Logger:
    return logging.getLogger(_concat_logging_path(PROCESS_OUTPUT_LOGGER_PREFIX, name))


NamedRecords = DefaultDict[str, List[logging.LogRecord]]


class _GroupedMemoryHandler(logging.handlers.MemoryHandler):
    def __init__(self, target: logging.Handler, capacity: int = 1024) -> None:
        super().__init__(capacity, target=target)
        self._named_records: NamedRecords = collections.defaultdict(list)

    def emit(self, record: logging.LogRecord) -> None:
        self._named_records[record.name.split(".")[-1]].append(record)

    def shouldFlush(self, record: logging.LogRecord) -> bool:
        return False

    def setFormatter(self, fmt: logging.Formatter) -> None:
        self.target: Optional[logging.Handler]
        assert self.target is not None
        self.target.setFormatter(fmt)

    def flush(self) -> None:
        names = sorted(self._named_records.keys())
        for name in names:
            for record in self._named_records[name]:
                super().emit(record)
        super().flush()
        self._named_records = collections.defaultdict(list)


def setup_logger(loglevel: int, pretty: bool = True) -> None:
    root_logger = logging.getLogger("pysen")
    root_logger.setLevel(loglevel)
    root_logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(_general_formatter(pretty))
    root_logger.addHandler(handler)


class _LoggingUnit:
    def __init__(
        self, loglevel: int, is_grouped: bool, pretty: bool, is_process_enabled: bool
    ) -> None:
        self._loglevel = loglevel
        self._is_grouped = is_grouped
        self._pretty = pretty
        self._is_process_enabled = is_process_enabled
        self._handler = self._create_handler()

    def setup(self) -> None:
        self._handler.setLevel(logging.DEBUG)
        self._handler.setFormatter(self._create_formatter())
        pysen_root_logger.addHandler(self._handler)
        reporter_root_logger.setLevel(self._loglevel)
        if self._is_process_enabled:
            process_output_root_logger.propagate = True

    def finalize(self) -> None:
        self._handler.flush()
        pysen_root_logger.removeHandler(self._handler)
        process_output_root_logger.propagate = False

    def _create_handler(self) -> logging.Handler:
        if self._is_grouped:
            return _GroupedMemoryHandler(target=logging.StreamHandler())
        else:
            return logging.StreamHandler()

    def _create_formatter(self) -> logging.Formatter:
        if self._pretty:
            ret: logging.Formatter = _CustomColoredFormatter(
                "%(log_color)s%(message)s",
                log_colors=_logging_output_colors,
            )
            return ret
        else:
            return logging.Formatter("%(message)s")


def _general_formatter(pretty: bool) -> logging.Formatter:
    if pretty:
        ret: logging.Formatter = ColoredFormatter("%(log_color)s%(message)s")
        return ret
    else:
        return logging.Formatter("%(message)s")


def _get_process_output_level_name(loglevel: int) -> str:
    if loglevel <= logging.INFO:
        return _PROCESS_STDOUT
    else:
        return _PROCESS_STDERR


class _CustomColoredFormatter(colorlog.ColoredFormatter):  # type: ignore
    def format(self, record: logging.LogRecord) -> str:
        if record.name.startswith(PROCESS_OUTPUT_LOGGER_PREFIX):
            record.levelname = _get_process_output_level_name(record.levelno)

        return cast(str, super().format(record))


@dataclasses.dataclass(frozen=True)
class CommandLoggingOptions:
    is_grouped: bool
    pretty: bool
    process_output: bool

    @contextlib.contextmanager
    def start_logging(self, loglevel: int) -> Iterator[None]:
        unit = _LoggingUnit(loglevel, self.is_grouped, self.pretty, self.process_output)
        unit.setup()

        try:
            yield
        finally:
            unit.finalize()
