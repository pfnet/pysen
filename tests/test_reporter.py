import pathlib
from unittest import mock

import pytest

from pysen.diagnostic import Diagnostic, FLCMFormatter
from pysen.reporter import (
    _COMMAND_REPR_MAX_LENGTH,
    _OMIT_REPR,
    Reporter,
    ReporterFactory,
    _truncate_command_sequence,
)

BASE_DIR = pathlib.Path(__file__).resolve().parent


def test_reporter() -> None:
    r = Reporter("fuga")

    with pytest.raises(AssertionError):
        r.success

    with pytest.raises(AssertionError):
        r.elapsed_time

    with mock.patch("time.time") as m:
        m.return_value = 100.0
        with r:
            assert r.name == "fuga"
            r.report_command("command --flag")
            r.set_result(True, 0)

            m.return_value = 123.4

    assert r.elapsed_time == pytest.approx(23.4)
    assert r.success

    r = Reporter("piyo")
    with r:
        assert r.name == "piyo"
        r.set_result(False, 128)

    assert not r.success


def test_reporter_report_diagnostics() -> None:
    r = Reporter("foo")
    d1 = Diagnostic(pathlib.Path("hoge").resolve(), 1, 2, 3, message="hoge")
    d2 = Diagnostic(pathlib.Path("fuga").resolve(), 4, 5, 6, message="fuga")
    d3 = Diagnostic(pathlib.Path("piyo").resolve(), 7, 8, 9, message="piyo")

    with r:
        r.report_diagnostics([d1])
        assert r.diagnostics == [d1]

        r.report_diagnostics([d2, d3])
        assert r.diagnostics == [d1, d2, d3]


def test_reporter_factory() -> None:
    factory = ReporterFactory()
    assert len(factory.reporters) == 0

    with factory.create("foo") as r:
        r.set_result(True, 0)
        r.report_diagnostics(
            [Diagnostic(BASE_DIR / "hoge.py", 1, 2, 3, message="error")]
        )

    assert len(factory.reporters) == 1
    assert not factory.has_error()
    out = factory.format_summary()
    assert "foo" in out

    with factory.create("bar") as r:
        r.set_result(False, 128)

    assert len(factory.reporters) == 2
    assert factory.has_error()
    out = factory.format_summary()
    assert "foo" in out and "bar" in out

    err_summary = factory.format_error_summary()
    assert "\n - bar\n" in err_summary and "foo" not in err_summary

    out = factory.format_diagnostic_summary(FLCMFormatter)
    assert f"{BASE_DIR / 'hoge.py'}:1:3:foo: error" in out


def test__truncate_command_sequence() -> None:
    assert _truncate_command_sequence("abcde") == "abcde"

    str_a = "a" * _COMMAND_REPR_MAX_LENGTH
    assert _truncate_command_sequence(str_a) == str_a

    def assert_truncated(original: str, formatted: str) -> None:
        assert original != formatted
        assert formatted.endswith(_OMIT_REPR)
        assert len(formatted) == _COMMAND_REPR_MAX_LENGTH

    str_b = str_a + "a"
    assert_truncated(str_b, _truncate_command_sequence(str_b))

    str_c = str_a + "a" * 100
    assert_truncated(str_c, _truncate_command_sequence(str_c))
