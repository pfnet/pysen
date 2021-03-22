import difflib
import logging
import pathlib
from abc import abstractmethod
from typing import Iterable, List, Optional, Sequence, Set

from . import git_utils
from .command import CommandBase
from .error_lines import parse_error_diffs
from .reporter import Reporter
from .source import FilePredicateType, Source


class LintCommandBase(CommandBase):
    def __init__(self, base_dir: pathlib.Path, source: Source) -> None:
        self._base_dir = base_dir
        self._source = source

    def _get_sources(
        self, reporter: Reporter, filter_predicate: FilePredicateType
    ) -> Set[pathlib.Path]:
        return self.source.resolve_files(
            self.base_dir,
            filter_predicate,
            self.git_enabled(),
            reporter,
        )

    def _get_covered_files(
        self,
        reporter: Reporter,
        files: Sequence[pathlib.Path],
        filter_predicate: FilePredicateType,
    ) -> List[pathlib.Path]:
        sources = self._get_sources(reporter, filter_predicate)
        covered: List[pathlib.Path] = []

        for f in files:
            if f in sources:
                covered.append(f)
            else:
                reporter.logger.info(f"Skipping {f} for {self.name}")

        return covered

    @property
    def base_dir(self) -> pathlib.Path:
        return self._base_dir

    def git_enabled(self) -> bool:
        return git_utils.check_git_available(self.base_dir)

    @property
    def source(self) -> Source:
        return self._source


class SingleFileLintCommandBase(LintCommandBase):
    def _run(self, reporter: Reporter, file_paths: Iterable[pathlib.Path]) -> int:
        # NOTE(igarashi): create a list to evaluate check() for all file paths
        if all([self.check(file_path, reporter) for file_path in file_paths]):
            return 0
        else:
            return 1

    def __call__(self, reporter: Reporter) -> int:
        file_paths = self._get_sources(reporter, self.filter)
        reporter.logger.info(f"Checking {len(file_paths)} files")
        return self._run(reporter, file_paths)

    def run_files(self, reporter: Reporter, files: Sequence[pathlib.Path]) -> int:
        covered_files = self._get_covered_files(reporter, files, self.filter)
        return self._run(reporter, covered_files)

    @abstractmethod
    def filter(self, file_path: pathlib.Path) -> bool:
        ...

    @abstractmethod
    def check(self, file_path: pathlib.Path, reporter: Reporter) -> bool:
        ...


class SingleFileFormatCommandBase(SingleFileLintCommandBase):
    def __init__(
        self, base_dir: pathlib.Path, source: Source, inplace_edit: bool
    ) -> None:
        super().__init__(base_dir, source)
        self._inplace_edit = inplace_edit

    @property
    def inplace_edit(self) -> bool:
        return self._inplace_edit

    def check(self, file_path: pathlib.Path, reporter: Reporter) -> bool:
        formatted = self.format(file_path, reporter)
        if formatted is None:
            return False

        if self._inplace_edit:
            with file_path.open(mode="w") as f:
                f.write(formatted)
            return True

        else:
            with file_path.open() as f:
                original = f.readlines()
            diff = "".join(
                difflib.unified_diff(
                    original,
                    formatted.splitlines(True),
                    fromfile=str(file_path),
                    tofile=str(file_path),
                )
            )
            if len(diff) == 0:
                return True
            else:
                reporter.process_output.log(logging.INFO, diff)
                diagnostics = parse_error_diffs(
                    diff, lambda _: file_path, logger=reporter.logger
                )
                reporter.report_diagnostics(list(diagnostics))
                return False

    @abstractmethod
    def format(self, file_path: pathlib.Path, reporter: Reporter) -> Optional[str]:
        """Returns formatted content without modifying the original file.
        Note:
            If a file cannot be formatted due to its content (e.g. invalid syntax),
            this method should return `None`.
            In this case, `SingleFileFormatCommandBase` continues to check other files.
        """
        ...
