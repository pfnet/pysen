import dataclasses
import logging
from typing import Iterator, List, Tuple
from unittest import mock

import colorlog
import pytest

from pysen import logging_utils

SetupLoggerArgsType = Tuple[logging.Logger, int, logging.Handler]


@pytest.fixture
def mock_setup_logger() -> Iterator[List[SetupLoggerArgsType]]:
    args: List[SetupLoggerArgsType] = []

    def record(logger: logging.Logger, level: int, handler: logging.Handler) -> None:
        args.append((logger, level, handler))

    with mock.patch("pysen.logging_utils._setup_logger", side_effect=record):
        yield args


class TargetHandler(logging.Handler):
    def __init__(self) -> None:
        self.calls: List[str] = []
        super().__init__()

    def emit(self, record: logging.LogRecord) -> None:
        self.calls.append(record.msg)


def test_grouped_memory_handler() -> None:
    t_handler = TargetHandler()
    g_handler = logging_utils._GroupedMemoryHandler(target=t_handler)

    root_logger = logging.getLogger("test_logger")
    isort_logger = logging.getLogger("test_logger.isort")
    black_logger = logging.getLogger("test_logger.black")
    root_logger.addHandler(g_handler)

    root_logger.error("one")
    isort_logger.error("isort1")
    black_logger.error("black1")
    root_logger.error("two")
    isort_logger.error("isort2")
    black_logger.error("black2")

    g_handler.flush()

    assert t_handler.calls == ["black1", "black2", "isort1", "isort2", "one", "two"]

    formatter = logging.Formatter()
    g_handler.setFormatter(formatter)
    assert t_handler.formatter == formatter


def test__get_process_output_level_name() -> None:
    assert (
        logging_utils._get_process_output_level_name(logging.INFO)
        == logging_utils._PROCESS_STDOUT
    )
    assert (
        logging_utils._get_process_output_level_name(logging.ERROR)
        == logging_utils._PROCESS_STDERR
    )


@dataclasses.dataclass(frozen=True)
class ReporterLoggingUnitCondition:
    is_grouped: bool
    pretty: bool


def get_handler(logging_unit: logging_utils._LoggingUnit) -> logging.Handler:
    logging_unit.setup()
    handler = logging_utils.pysen_root_logger.handlers[0]
    # finalize to remove handler for ensuing tests
    logging_unit.finalize()
    return handler


class TestReporterLoggingUnit:
    def test_setup(self) -> None:
        def _get_handler(
            loglevel: int, is_grouped: bool, pretty: bool
        ) -> logging.Handler:
            return get_handler(
                logging_utils._LoggingUnit(
                    loglevel, is_grouped, pretty, is_process_enabled=True
                )
            )

        level = logging.INFO
        handler1 = _get_handler(level, True, True)
        assert isinstance(handler1, logging_utils._GroupedMemoryHandler)
        assert isinstance(handler1.target, logging.StreamHandler)
        assert isinstance(handler1.target.formatter, colorlog.ColoredFormatter)
        assert (
            handler1.target.formatter.log_colors == logging_utils._logging_output_colors
        )

        handler2 = _get_handler(level, True, False)
        assert isinstance(handler2, logging_utils._GroupedMemoryHandler)
        assert isinstance(handler2.target, logging.StreamHandler)
        assert handler2.target.formatter is not None
        assert handler2.target.formatter._fmt == "%(message)s"

        handler3 = _get_handler(level, False, True)
        assert isinstance(handler3, logging.StreamHandler)
        assert isinstance(handler3.formatter, colorlog.ColoredFormatter)
        assert handler3.formatter.log_colors == logging_utils._logging_output_colors

        handler4 = _get_handler(level, False, False)
        assert isinstance(handler4, logging.StreamHandler)
        assert handler4.formatter is not None
        assert handler4.formatter._fmt == "%(message)s"

    def test_setup_finalize(self) -> None:
        level = logging.DEBUG
        is_grouped = True
        pretty = True
        is_enabled = True

        root_logger = logging_utils.pysen_root_logger
        unit = logging_utils._LoggingUnit(level, is_grouped, pretty, is_enabled)

        unit.setup()
        assert logging_utils.reporter_root_logger.level == level
        assert logging_utils.process_output_root_logger.level == logging.INFO

        assert len(root_logger.handlers) == 1
        handler = root_logger.handlers[0]
        assert isinstance(handler, logging_utils._GroupedMemoryHandler)
        assert isinstance(handler.target, logging.StreamHandler)
        assert handler.level == level

        reporter_logger = logging_utils.get_reporter_logger("hoge")
        process_logger = logging_utils.get_process_output_logger("hoge")
        process2_logger = logging_utils.get_process_output_logger("fuga")

        reporter_logger.info("foo")
        assert len(handler._named_records) == 1
        process_logger.info("bar")
        assert len(handler._named_records) == 1
        process2_logger.info("baz")
        assert len(handler._named_records) == 2

        unit.finalize()
        # the buffer should be empty because we flushed
        assert len(handler._named_records) == 0
        assert len(root_logger.handlers) == 0
