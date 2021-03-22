import io
import logging
import os
import pathlib
import tempfile
from typing import List

import pytest

from pysen.process_utils import _read_stream, run
from pysen.reporter import Reporter

SAMPLE_DATA = """BytesIO example string.

Motivation-Driven
Learn or Die
Proud, but Humble
Boldly do what no one has done before"""

SAMPLE_SCRIPT = """#!/bin/bash
# This string is used to check if trailing new lines are kept.

echo "Start"
echo "StartError" > /dev/stderr

# Test sleep
sleep 0.1

for x in {0..99}
do
  echo "out${x}"
  echo "err${x}" > /dev/stderr
done

echo "End"
echo "EndError" > /dev/stderr

"""


class FakeHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self._messages: List[str] = []

    @property
    def messages(self) -> List[str]:
        return self._messages

    def emit(self, record: logging.LogRecord) -> None:
        self._messages.append(record.msg)


class HandlerException(Exception):
    pass


class FailingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        raise HandlerException("somebody screwded up")


@pytest.mark.parametrize(
    "sample_str",
    [SAMPLE_DATA, SAMPLE_SCRIPT],
    ids=["sample", "sample_with_trailing_newlines"],
)
def test__read_stream(sample_str: str) -> None:
    # NOTE(igarashi): Since BytesIO does not inherit RawIOBase but BufferedIOBase,
    # we cannot instantiate BufferedReader from bytes directly.
    # We use FileIOBase instead.
    with tempfile.TemporaryDirectory() as td:
        temp_dir = pathlib.Path(td)
        temp_path = temp_dir / "file"
        temp_path.write_text(sample_str)

        reporter = Reporter("foo")
        handler = FakeHandler()
        reporter.process_output.setLevel(logging.INFO)
        reporter.process_output.handlers.clear()
        reporter.process_output.addHandler(handler)

        ret = _read_stream(io.BytesIO(temp_path.read_bytes()), reporter, logging.INFO)
        expected = sample_str
        assert ret == expected
        assert handler.messages == expected.splitlines()

        handler.messages.clear()
        ret = _read_stream(io.BytesIO(temp_path.read_bytes()), reporter, logging.DEBUG)

        assert ret == expected
        assert handler.messages == []


def test_run() -> None:
    assert os.getenv("LANG", "C") == "C", "Did you run pytest through tox?"
    with tempfile.TemporaryDirectory() as td:
        temp_dir = pathlib.Path(td)
        temp_path = temp_dir / "file"
        temp_path.touch()

        reporter = Reporter("foo")
        handler = FakeHandler()
        reporter.process_output.setLevel(logging.INFO)
        reporter.process_output.handlers.clear()
        reporter.process_output.addHandler(handler)

        ret, stdout, stderr = run(["ls", str(temp_path)], reporter)
        assert ret == 0
        assert "file" in stdout
        assert stderr == ""
        assert len(handler.messages) > 0

        handler.messages.clear()
        ret, stdout, stderr = run(
            ["ls", str(temp_path)], reporter, stdout_loglevel=logging.NOTSET
        )
        assert ret == 0
        assert "file" in stdout
        assert stderr == ""
        assert len(handler.messages) == 0

        handler.messages.clear()
        ret, stdout, stderr = run(["ls", str(temp_dir / "invalid")], reporter)
        assert ret != 0
        assert stdout == ""
        assert "No such file or directory" in stderr
        assert len(handler.messages) > 0

        handler.messages.clear()
        ret, stdout, stderr = run(
            ["ls", str(temp_dir / "invalid")], reporter, stderr_loglevel=logging.DEBUG
        )
        assert ret != 0
        assert stdout == ""
        assert "No such file or directory" in stderr
        assert len(handler.messages) == 0

        # check if run method can handle large output and errors
        temp_path.write_text(SAMPLE_SCRIPT)

        ret, stdout, stderr = run(["bash", str(temp_path)], reporter)

        stdout_lines = stdout.splitlines()
        stderr_lines = stderr.splitlines()

        assert len(stdout_lines) == 102
        assert len(stderr_lines) == 102

        assert stdout_lines[0] == "Start" and stderr_lines[0] == "StartError"
        assert stdout_lines[-1] == "End" and stderr_lines[-1] == "EndError"

        for x in range(100):
            assert stdout_lines[x + 1] == f"out{x}"
            assert stderr_lines[x + 1] == f"err{x}"

        # exceptions encountered in sub-threads shall be raised
        reporter.process_output.addHandler(FailingHandler())
        with pytest.raises(HandlerException):
            ret, stdout, stderr = run(["echo", "mashimashi"], reporter)
