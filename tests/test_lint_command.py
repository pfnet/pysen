import logging
import pathlib
from tempfile import TemporaryDirectory
from typing import List, Optional, Set
from unittest import mock

from pysen.diagnostic import Diagnostic
from pysen.lint_command import (
    LintCommandBase,
    SingleFileFormatCommandBase,
    SingleFileLintCommandBase,
)
from pysen.reporter import Reporter
from pysen.source import FilePredicateType, Source

BASE_DIR = pathlib.Path(__file__).resolve().parent


class FakeLintCommand(LintCommandBase):
    @property
    def name(self) -> str:
        return "fake"

    def __call__(self, reporter: Reporter) -> int:
        pass


class FakeHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self._messages: List[str] = []

    @property
    def messages(self) -> List[str]:
        return self._messages

    def emit(self, record: logging.LogRecord) -> None:
        self._messages.append(record.msg)


class FakeSource(Source):
    def resolve_files(
        self,
        base_dir: pathlib.Path,
        filter_predicate: Optional[FilePredicateType],
        use_git: bool = True,
        reporter: Optional[Reporter] = None,
    ) -> Set[pathlib.Path]:
        assert filter_predicate is not None

        files = filter(
            filter_predicate, map(pathlib.Path, ["foo.py", "bar.pyi", "baz.txt"])
        )
        return {base_dir / f for f in files}


class FakeSingleFileLintCommand(SingleFileLintCommandBase):
    @property
    def name(self) -> str:
        return "fake"

    def filter(self, file_path: pathlib.Path) -> bool:
        return file_path.suffix in {".py", ".pyi"}

    def check(self, file_path: pathlib.Path, reporter: Reporter) -> bool:
        pass


class FakeSingleFileFormatCommand(SingleFileFormatCommandBase):
    @property
    def name(self) -> str:
        return "fake"

    def filter(self, file_path: pathlib.Path) -> bool:
        return file_path.suffix in {".py", ".pyi"}

    def format(self, file_path: pathlib.Path, reporter: Reporter) -> Optional[str]:
        pass


def test_lint_command_base() -> None:
    source = Source()
    command = FakeLintCommand(BASE_DIR, source)

    assert command.name == "fake"
    assert command.base_dir == BASE_DIR
    assert command.source == source

    with mock.patch("pysen.git_utils.check_git_available", return_value=True):
        assert command.git_enabled()

    with mock.patch("pysen.git_utils.check_git_available", return_value=False):
        assert not command.git_enabled()


def test_single_file_lint_command_base() -> None:
    with TemporaryDirectory() as t:
        base_dir = pathlib.Path(t)

        for file_path in {"foo.py", "bar.pyi", "baz.txt"}:
            (base_dir / file_path).touch()

        command = FakeSingleFileLintCommand(base_dir, FakeSource())
        with mock.patch.object(command, "check", return_value=True) as check:
            reporter = Reporter("fake")
            handler = FakeHandler()
            reporter.process_output.addHandler(handler)
            assert command(reporter) == 0
            assert check.call_count == 2
            assert len(handler.messages) == 0
            assert len(reporter.diagnostics) == 0

        with mock.patch.object(command, "check") as check:
            check.side_effect = [True, False]
            reporter = Reporter("fake")
            handler = FakeHandler()
            reporter.process_output.addHandler(handler)
            assert command(reporter) == 1
            assert check.call_count == 2
            assert len(handler.messages) == 0
            assert len(reporter.diagnostics) == 0


def test_single_file_format_command_base() -> None:
    with TemporaryDirectory() as t:
        base_dir = pathlib.Path(t)

        for file_path in {"foo.py", "bar.pyi", "baz.txt"}:
            (base_dir / file_path).touch()

        command = FakeSingleFileFormatCommand(
            base_dir, FakeSource(), inplace_edit=False
        )
        with mock.patch.object(command, "format", return_value="") as format_method:
            reporter = Reporter("fake")
            handler = FakeHandler()
            reporter.process_output.addHandler(handler)
            assert command(reporter) == 0
            assert format_method.call_count == 2
            assert len(handler.messages) == 0
            assert len(reporter.diagnostics) == 0

        with mock.patch.object(command, "format", return_value="diff") as format_method:
            reporter = Reporter("fake")
            handler = FakeHandler()
            reporter.process_output.addHandler(handler)
            assert command(reporter) == 1
            assert format_method.call_count == 2
            assert len(handler.messages) == 2
            assert len(reporter.diagnostics) == 2
            for file_path in {"foo.py", "bar.pyi"}:
                assert (
                    f"--- {base_dir / file_path}\n"
                    f"+++ {base_dir / file_path}\n"
                    "@@ -0,0 +1 @@\n"
                    "+diff"
                ) in handler.messages
                assert (
                    Diagnostic(
                        start_line=1,
                        end_line=1,
                        start_column=1,
                        file_path=base_dir / file_path,
                        diff="+diff",
                    )
                    in reporter.diagnostics
                )

        command = FakeSingleFileFormatCommand(base_dir, FakeSource(), inplace_edit=True)
        with mock.patch.object(command, "format", return_value=None) as format_method:
            reporter = Reporter("fake")
            handler = FakeHandler()
            reporter.process_output.addHandler(handler)
            assert command(reporter) == 1
            assert format_method.call_count == 2
            assert len(handler.messages) == 0
            assert len(reporter.diagnostics) == 0
            with (base_dir / "foo.py").open() as f:
                assert f.read() == ""
            with (base_dir / "bar.pyi").open() as f:
                assert f.read() == ""

        with mock.patch.object(command, "format", return_value="diff") as format_method:
            reporter = Reporter("fake")
            handler = FakeHandler()
            reporter.process_output.addHandler(handler)
            assert command(reporter) == 0
            assert format_method.call_count == 2
            assert len(handler.messages) == 0
            assert len(reporter.diagnostics) == 0
            with (base_dir / "foo.py").open() as f:
                assert f.read() == "diff"
            with (base_dir / "bar.pyi").open() as f:
                assert f.read() == "diff"
