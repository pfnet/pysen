import argparse
import dataclasses
import enum
import logging
import pathlib
import sys
from typing import Optional, Sequence, Tuple

from . import __version__, cli_config, exceptions
from .cli_config import CliConfig
from .diagnostic import DiagnosticFormatter, FLCMFormatter
from .logging_utils import setup_logger
from .manifest import ManifestBase
from .path import wrap_path
from .pyproject import find_pyproject, load_manifest
from .reporter import ReporterFactory
from .runner import Runner
from .runner_options import RunOptions

CLI_DESCRIPTION = "pysen CLI"


_ErrorFormat = {
    "gnu": FLCMFormatter,
}


@dataclasses.dataclass
class _SetupOptions:
    error_formatter: Optional[DiagnosticFormatter]
    options: RunOptions
    loglevel: int
    process_output: bool


@enum.unique
class LogLevel(enum.Enum):
    debug = logging.DEBUG
    info = logging.INFO
    warning = logging.WARNING
    error = logging.ERROR


@enum.unique
class ProcessOutputMode(enum.Enum):
    auto = enum.auto()
    show = enum.auto()
    hide = enum.auto()


def _get_loglevel(user_specification: Optional[str], default: int) -> int:
    if user_specification is None:
        return default
    else:
        ret: int = LogLevel[user_specification].value
        return ret


def _is_process_output_requested(user_specification: str, default: bool) -> bool:
    user_specification_mode = ProcessOutputMode[user_specification]
    return user_specification_mode == ProcessOutputMode.show or (
        user_specification_mode == ProcessOutputMode.auto and default
    )


def _use_pretty_logging() -> bool:
    return sys.stderr.isatty()


def _show_version() -> None:
    print(__version__)


def _setup_run(
    base_dir: pathlib.Path,
    args: argparse.Namespace,
    config: Optional[CliConfig],
) -> _SetupOptions:
    error_formatter: Optional[DiagnosticFormatter] = None
    default_loglevel = logging.INFO
    if args.error_format is not None:
        error_formatter = _ErrorFormat[args.error_format]
        default_loglevel = logging.WARNING

    # setup logger again with new configuration
    loglevel = _get_loglevel(args.loglevel, default_loglevel)
    setup_logger(loglevel, pretty=_use_pretty_logging())
    process_output = _is_process_output_requested(
        args.process_output, error_formatter is None
    )

    options = RunOptions(
        require_diagnostics=error_formatter is not None, no_parallel=args.no_parallel
    )
    return _SetupOptions(error_formatter, options, loglevel, process_output)


def _run_target(
    target_name: str,
    runner: Runner,
    base_dir: pathlib.Path,
    args: argparse.Namespace,
    files: Optional[Sequence[pathlib.Path]],
    setup_options: _SetupOptions,
    config: Optional[CliConfig],
) -> None:
    settings_dir: Optional[pathlib.Path] = None
    if config is not None:
        settings_dir = config.settings_dir

    reporter_factory = ReporterFactory(
        pretty=_use_pretty_logging(),
        process_output=setup_options.process_output,
        loglevel=setup_options.loglevel,
    )
    try:
        runner.run(
            target_name,
            base_dir,
            args,
            reporter_factory,
            setup_options.options,
            settings_dir=settings_dir,
            files=files,
        )
    except exceptions.CommandNotFoundError:
        sys.stderr.write(f"target: {target_name} not found\n")
        sys.exit(1)

    error_exit = reporter_factory.has_error()

    if setup_options.error_formatter is None:
        print("\n ** execution summary **")
        print(reporter_factory.format_summary())
        if error_exit:
            sys.stderr.write(f"{target_name} finished with error(s)\n")
            print(reporter_factory.format_error_summary())
    else:
        ret = reporter_factory.format_diagnostic_summary(setup_options.error_formatter)
        if reporter_factory.has_error():
            print(ret)
            print(reporter_factory.format_error_summary(), file=sys.stderr)
        else:
            print("No errors found")

    if error_exit:
        sys.exit(1)


def _start_run(
    base_dir: pathlib.Path,
    runner: Runner,
    config: Optional[CliConfig],
    args: argparse.Namespace,
) -> None:
    target_names = args.targets
    setup_options = _setup_run(base_dir, args, config)
    for target_name in target_names:
        _run_target(
            target_name=target_name,
            runner=runner,
            base_dir=base_dir,
            args=args,
            files=None,
            setup_options=setup_options,
            config=config,
        )


def _start_run_files(
    base_dir: pathlib.Path,
    runner: Runner,
    config: Optional[CliConfig],
    args: argparse.Namespace,
) -> None:
    target_name = args.target
    files = [pathlib.Path(p).resolve() for p in args.files]
    for p in files:
        if not p.exists():
            raise FileNotFoundError(f"{p} does not exist")

    setup_options = _setup_run(base_dir, args, config)
    _run_target(
        target_name=target_name,
        runner=runner,
        base_dir=base_dir,
        args=args,
        files=files,
        setup_options=setup_options,
        config=config,
    )


def _start_generate(
    base_dir: pathlib.Path,
    runner: Runner,
    config: Optional[CliConfig],
    args: argparse.Namespace,
) -> None:
    # NOTE(igarashi): args.export_dir must be resolved by cwd(), not base_dir
    # since it is a cli argument
    settings_dir: pathlib.Path = pathlib.Path(args.export_dir).resolve()
    settings_dir.mkdir(parents=True, exist_ok=True)
    runner.export_settings(base_dir, settings_dir, args)


def _start_list(
    base_dir: pathlib.Path,
    runner: Runner,
    config: Optional[CliConfig],
    args: argparse.Namespace,
) -> None:
    targets = runner.get_targets(args)
    print("available targets:")
    for name, target in targets.items():
        print(f" * {name}")
        for c in target:
            print(f"   - {c}")


def _setup_manifest_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=CLI_DESCRIPTION, add_help=False)
    parser.add_argument(
        "--config",
        type=str,
        help="Path for pyproject.toml",
        default=None,
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show pysen version and exit",
    )
    parser.add_argument(
        "--loglevel",
        type=str,
        help="Set loglevel",
        choices=list(LogLevel.__members__),
    )
    parser.add_argument(
        "--process-output",
        type=str,
        help="Process output control",
        default="auto",
        dest="process_output",
        choices=list(ProcessOutputMode.__members__),
    )
    parser.add_argument(
        "-s",
        action="store_const",
        help="Shortcut for --process-output=show",
        const="show",
        dest="process_output",
    )
    return parser


def _parse_manifest_options() -> Tuple[ManifestBase, Optional[CliConfig], pathlib.Path]:
    # NOTE(igarashi): show detailed help to the user when a configuration is available
    # In this method, we
    # - try to load an available pyproject.toml file
    # - show the help when `--help` is set and pysen cannot load any config
    # - `--help` is handled by `main` parser in `cli()` method in order to show detailed help
    #    when a config is successfully loaded
    parser = _setup_manifest_parser()
    args, unknown = parser.parse_known_args()

    if args.version:
        _show_version()
        sys.exit(0)

    setup_logger(
        _get_loglevel(args.loglevel, logging.INFO), pretty=_use_pretty_logging()
    )

    path: Optional[pathlib.Path] = None
    if args.config is not None:
        path = wrap_path(args.config)
    try:
        pyproject_path = find_pyproject(path)
    except FileNotFoundError as e:
        if "--help" in unknown or "-h" in unknown:
            parser.print_help()
            sys.exit(0)

        sys.stderr.write(f"{e}\n")
        sys.exit(1)

    try:
        manifest = load_manifest(pyproject_path)
        config = cli_config.parse(pyproject_path)
    except exceptions.PysenError as e:
        sys.stderr.write(f"error occured while loading {pyproject_path}: {e}\n")
        sys.exit(1)

    base_dir = pyproject_path.parent
    return manifest, config, base_dir


def cli() -> None:
    manifest, config, base_dir = _parse_manifest_options()
    runner = Runner(manifest)

    root_parser = _setup_manifest_parser()
    manifest_parser = argparse.ArgumentParser(
        description=CLI_DESCRIPTION,
        parents=[root_parser],
        add_help=False,
    )
    runner.setup_manifest_argparse(
        manifest_parser.add_argument_group("manifest options")
    )
    manifest_args, _ = manifest_parser.parse_known_args()

    action_parser = argparse.ArgumentParser(parents=[manifest_parser], add_help=True)
    subparsers = action_parser.add_subparsers()
    run_parser = subparsers.add_parser("run", help="run target")
    run_parser.add_argument(
        "targets",
        type=str,
        help="target to run",
        choices=runner.get_targets(manifest_args),
        nargs="+",
    )
    run_parser.add_argument(
        "--error-format", type=str, choices=_ErrorFormat.keys(), default=None
    )
    run_parser.add_argument("--no-parallel", action="store_true")
    run_parser.set_defaults(func=_start_run)

    run_files_parser = subparsers.add_parser(
        "run_files", help="run target with a specified file"
    )
    run_files_parser.add_argument(
        "target",
        type=str,
        help="target to run",
        choices=runner.get_targets(manifest_args),
    )
    run_files_parser.add_argument("files", type=str, help="target file", nargs="+")
    run_files_parser.add_argument(
        "--error-format", type=str, choices=_ErrorFormat.keys(), default=None
    )
    run_files_parser.add_argument("--no-parallel", action="store_true")
    run_files_parser.set_defaults(func=_start_run_files)

    generate_parser = subparsers.add_parser("generate", help="generate setting files")
    generate_parser.add_argument(
        "export_dir", type=str, help="target directory to export"
    )
    generate_parser.set_defaults(func=_start_generate)

    list_parser = subparsers.add_parser(
        "list", help="list available targets in manifest"
    )
    list_parser.set_defaults(func=_start_list)

    action_args = action_parser.parse_args()
    # for python 3.6 support, we cannot use add_subparsers(required=True)
    if "func" not in action_args:
        action_parser.print_help()
        sys.exit(1)

    action_args.func(base_dir, runner, config, action_args)
