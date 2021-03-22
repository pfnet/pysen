from unittest import mock

from pysen.cli import _use_pretty_logging


def test__use_pretty_logging() -> None:
    with mock.patch("sys.stderr.isatty", return_value=True):
        assert _use_pretty_logging()

    with mock.patch("sys.stderr.isatty", return_value=False):
        assert not _use_pretty_logging()
