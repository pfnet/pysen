import argparse
import concurrent.futures
import contextlib
import logging
import pathlib
import tempfile
from typing import Dict, List, Optional, Sequence

from . import path
from .command import CommandBase
from .exceptions import (
    CommandNotFoundError,
    InvalidCommandNameError,
    RunTargetFileNotSupported,
)
from .manifest import ManifestBase, ParserType, TargetType
from .reporter import ReporterFactory
from .runner_options import PathContext, RunOptions
from .types import ComponentName, TargetName

_logger = logging.getLogger(__name__)


def _verify_command_name(command: CommandBase) -> None:
    if ":" in command.name:
        raise InvalidCommandNameError(command.name)


def _has_side_effects(target: TargetType) -> bool:
    return any(cmd.has_side_effects for cmd in target)


def run_target(
    target: TargetType,
    reporters: ReporterFactory,
    options: RunOptions,
    files: Optional[Sequence[pathlib.Path]] = None,
) -> None:
    def run_cmd(cmd: CommandBase) -> bool:
        _verify_command_name(cmd)
        with reporters.create(cmd.name) as r:
            exit_code: int
            try:
                if files is not None:
                    exit_code = cmd.run_files(reporter=r, files=files)
                else:
                    exit_code = cmd.run(reporter=r)
            except CommandNotFoundError:
                exit_code = 127
                r.logger.exception("command not found")
            except RunTargetFileNotSupported:
                exit_code = 0
                r.logger.info(f"{cmd.name} does not support target file execution")
            except KeyboardInterrupt:
                exit_code = 130
                r.logger.exception("interrupted")
                return False
            except BaseException:
                exit_code = -1
                r.logger.exception("unexpected exception")
            finally:
                r.set_result(exit_code == 0, exit_code)
        return True

    if options.no_parallel:
        is_grouped = False
    else:
        is_grouped = not _has_side_effects(target)

    with reporters.logging_handlers(is_grouped=is_grouped):
        if is_grouped:
            # TODO: control the maximum number of concurrent threads
            _logger.info("Running commands concurrently...")
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.map(run_cmd, target)
            _logger.info("... concurrent execution done")
        else:
            _logger.info("Running commands")
            for cmd in target:
                if not run_cmd(cmd):
                    break


class Runner:
    def __init__(self, manifest: ManifestBase) -> None:
        self._manifest = manifest

    def setup_manifest_argparse(self, parser: ParserType) -> None:
        self._manifest.configure_parser(parser)

    def parse_manifest_arguments(self, args: Sequence[str]) -> argparse.Namespace:
        parser = argparse.ArgumentParser("manifest options")
        self.setup_manifest_argparse(parser)
        return parser.parse_args(args)

    def export_settings(
        self,
        base_dir: pathlib.Path,
        settings_dir: pathlib.Path,
        args: argparse.Namespace,
    ) -> None:
        self._manifest.export_settings(PathContext(base_dir, settings_dir), args)

    def get_targets(self, args: argparse.Namespace) -> Dict[str, List[ComponentName]]:
        return self._manifest.get_targets(args)

    def _get_target(
        self,
        target_name: TargetName,
        paths: PathContext,
        options: RunOptions,
        args: argparse.Namespace,
    ) -> TargetType:
        # NOTE(igarashi): make sure if target_name exists before calling get_target(target_name)
        targets = self.get_targets(args)
        if target_name not in targets:
            raise CommandNotFoundError(f"target: {target_name} not found")

        return self._manifest.get_target(target_name, paths, options, args)

    def run(
        self,
        target_name: str,
        base_dir: pathlib.Path,
        manifest_args: argparse.Namespace,
        reporters: ReporterFactory,
        options: RunOptions,
        settings_dir: Optional[pathlib.Path] = None,
        files: Optional[Sequence[pathlib.Path]] = None,
    ) -> None:
        with contextlib.ExitStack() as stack:
            base_dir = base_dir.resolve()
            if settings_dir is not None:
                settings_dir = path.resolve_path(base_dir, settings_dir)
                settings_dir.mkdir(parents=True, exist_ok=True)
            else:
                tempdir = stack.enter_context(tempfile.TemporaryDirectory())
                settings_dir = pathlib.Path(tempdir)

            paths = PathContext(base_dir, settings_dir)
            self.export_settings(paths.base_dir, paths.settings_dir, manifest_args)
            target = self._get_target(target_name, paths, options, manifest_args)
            run_target(target, reporters, options, files)
