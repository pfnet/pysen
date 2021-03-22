import math
import pathlib
import threading
import unittest.mock
from typing import Any, Callable, List, Optional, cast

import pytest
from _pytest.capture import CaptureFixture

from fakes.component import FakeCommand, FakeComponent, Operation
from fakes.manifest import FakeManifest
from pysen.command import CommandBase
from pysen.exceptions import CommandNotFoundError, InvalidCommandNameError
from pysen.manifest import Manifest, ManifestBase
from pysen.reporter import Reporter, ReporterFactory
from pysen.runner import Runner, _has_side_effects, _verify_command_name
from pysen.runner_options import PathContext, RunOptions

FAKE_PATH = pathlib.Path(__file__)
FixtureType = Callable[..., ManifestBase]


@pytest.fixture
def fake_manifest() -> FixtureType:
    def create(
        base_dir: pathlib.Path,
        settings_dir: Optional[pathlib.Path],
        ref: Optional[List[float]] = None,
        dumped: Optional[threading.Event] = None,
    ) -> ManifestBase:
        r = ref or [0.0]
        d = dumped or threading.Event()

        node1 = FakeComponent(
            "node1",
            {"op1": (2, Operation.MUL), "op2": (10, Operation.ADD)},
            base_dir,
            settings_dir,
            r,
        )
        node2 = FakeComponent(
            "node2",
            {"op1": (3, Operation.MUL), "op3": (-1, Operation.MUL)},
            base_dir,
            settings_dir,
            r,
        )

        def dump(*args: Any) -> None:
            d.set()

        return Manifest([node1, node2], dump_handler=dump)

    return create


@pytest.fixture
def fake_manifest_with_options() -> FixtureType:
    def create(
        base_dir: pathlib.Path,
        settings_dir: Optional[pathlib.Path],
        num_required: bool,
        ref: Optional[List[float]] = None,
    ) -> ManifestBase:
        r = ref or [0.0]
        options = RunOptions()

        items = {
            "op1": [
                FakeCommand(2, Operation.ADD, r, options),
                FakeCommand(10, Operation.MUL, r, options),
                FakeCommand(-1, Operation.ADD, r, options),
            ]
        }
        special_item = [
            FakeCommand(3, Operation.ADD, r, options),
            FakeCommand(2, Operation.MUL, r, options),
        ]

        ret = FakeManifest(base_dir, settings_dir, num_required, items, special_item)
        return cast(ManifestBase, ret)

    return create


def test_export_settings(fake_manifest: FixtureType) -> None:
    base_dir = pathlib.Path("/foo")
    settings_dir = pathlib.Path("/bar")
    dumped = threading.Event()
    manifest = fake_manifest(base_dir, settings_dir, dumped=dumped)
    runner = Runner(manifest)
    assert not dumped.is_set()
    args = runner.parse_manifest_arguments([])
    runner.export_settings(base_dir, settings_dir, args)
    assert dumped.is_set()


def test_get_targets(fake_manifest: FixtureType) -> None:
    paths = PathContext(pathlib.Path("/foo"), pathlib.Path("/bar"))
    manifest = fake_manifest(paths.base_dir, paths.settings_dir)
    runner = Runner(manifest)
    args = runner.parse_manifest_arguments([])
    targets = runner.get_targets(args)
    assert len(targets) == 3
    assert targets.keys() == {"op1", "op2", "op3"}
    assert len(targets["op1"]) == 2
    assert len(targets["op2"]) == 1
    assert len(targets["op3"]) == 1


def test_get_target(fake_manifest: FixtureType) -> None:
    paths = PathContext(pathlib.Path("/foo"), pathlib.Path("/bar"))
    options = RunOptions()
    manifest = fake_manifest(paths.base_dir, paths.settings_dir)
    runner = Runner(manifest)
    args = runner.parse_manifest_arguments([])
    assert len(runner._get_target("op1", paths, options, args)) == 2
    assert len(runner._get_target("op2", paths, options, args)) == 1
    assert len(runner._get_target("op3", paths, options, args)) == 1
    with pytest.raises(CommandNotFoundError):
        runner._get_target("op4", paths, options, args)


def test_parse_manifest_arguments(
    fake_manifest_with_options: FixtureType, capsys: CaptureFixture
) -> None:
    ref = [1.0]
    manifest = fake_manifest_with_options(
        pathlib.Path("/foo"), None, num_required=False, ref=ref
    )
    runner = Runner(manifest)

    parsed = runner.parse_manifest_arguments([])
    assert parsed.num == 0
    assert not parsed.special

    parsed = runner.parse_manifest_arguments(["--special"])
    assert parsed.num == 0
    assert parsed.special

    parsed = runner.parse_manifest_arguments(["--special", "--num", "5"])
    assert parsed.num == 5
    assert parsed.special

    capsys.readouterr()
    with pytest.raises(SystemExit):
        runner.parse_manifest_arguments(["--hoge"])
    out = capsys.readouterr()
    assert "error: unrecognized arguments" in out.err

    manifest = fake_manifest_with_options(
        pathlib.Path("/foo"), None, num_required=True, ref=ref
    )
    runner = Runner(manifest)

    capsys.readouterr()
    with pytest.raises(SystemExit):
        runner.parse_manifest_arguments([])
    out = capsys.readouterr()
    assert "the following arguments are required" in out.err

    parsed = runner.parse_manifest_arguments(["--num", "2"])
    assert parsed.num == 2
    assert not parsed.special


def test_run_with_settings_dir(fake_manifest: FixtureType) -> None:
    base_dir = pathlib.Path("/foo")
    settings_dir = pathlib.Path("/settings")
    options = RunOptions()
    ref = [1.0]
    manifest = fake_manifest(base_dir, settings_dir, ref)
    runner = Runner(manifest)
    reporters = ReporterFactory()

    manifest_args = runner.parse_manifest_arguments([])
    with unittest.mock.patch("pathlib.Path.mkdir") as mock:
        runner.run(
            "op1",
            base_dir,
            manifest_args,
            reporters,
            options,
            settings_dir=settings_dir,
            files=None,
        )
        mock.assert_called()
    assert math.isclose(ref[0], 6.0)
    assert not reporters.has_error()


def test_run(fake_manifest: FixtureType) -> None:
    base_dir = pathlib.Path("/foo")
    ref = [1.0]
    manifest = fake_manifest(base_dir, None, ref)
    runner = Runner(manifest)
    reporters = ReporterFactory()
    options = RunOptions()

    manifest_args = runner.parse_manifest_arguments([])
    runner.run(
        "op1",
        base_dir,
        manifest_args=manifest_args,
        reporters=reporters,
        options=options,
        files=None,
    )
    assert math.isclose(ref[0], 6.0)
    assert not reporters.has_error()

    ref[0] = 1.0
    runner.run(
        "op2",
        base_dir,
        manifest_args=manifest_args,
        reporters=reporters,
        options=options,
        files=None,
    )
    assert math.isclose(ref[0], 11.0)
    assert not reporters.has_error()

    ref[0] = 1.0
    runner.run(
        "op3",
        base_dir,
        manifest_args=manifest_args,
        reporters=reporters,
        options=options,
        files=None,
    )
    assert math.isclose(ref[0], -1.0)
    assert reporters.has_error()
    reporter = next(r for r in reporters._reporters if r.name == "* -1")
    assert len(reporter.diagnostics) == 1

    # check if options is correctly handled in Command through runner.run
    reporters = ReporterFactory()
    options = RunOptions(require_diagnostics=False)
    ref[0] = 1.0
    runner.run(
        "op3",
        base_dir,
        manifest_args=manifest_args,
        reporters=reporters,
        options=options,
        files=None,
    )
    assert math.isclose(ref[0], -1.0)
    assert reporters.has_error()
    reporter = next(r for r in reporters._reporters if r.name == "* -1")
    assert len(reporter.diagnostics) == 0

    reporters = ReporterFactory()

    with pytest.raises(CommandNotFoundError):
        runner.run(
            "op4",
            base_dir,
            manifest_args=manifest_args,
            reporters=reporters,
            options=options,
            files=None,
        )

    ref[0] = 1.0
    manifest_args = runner.parse_manifest_arguments(["--enable", "node1"])
    runner.run(
        "op1",
        base_dir,
        manifest_args=manifest_args,
        reporters=reporters,
        options=options,
        files=None,
    )
    assert math.isclose(ref[0], 2.0)


def test_run_manifest_args(fake_manifest_with_options: FixtureType) -> None:
    base_dir = pathlib.Path("/foo")
    ref = [1.0]
    manifest = fake_manifest_with_options(base_dir, None, num_required=False, ref=ref)
    runner = Runner(manifest)
    reporters = ReporterFactory()
    options = RunOptions()

    parsed = runner.parse_manifest_arguments([])
    runner.run(
        "op1",
        base_dir,
        manifest_args=parsed,
        reporters=reporters,
        options=options,
        files=None,
    )
    assert math.isclose(ref[0], 29.0)
    assert not reporters.has_error()

    ref[0] = 1.0
    parsed = runner.parse_manifest_arguments([])
    with pytest.raises(CommandNotFoundError):
        runner.run(
            "special",
            base_dir,
            manifest_args=parsed,
            reporters=reporters,
            options=options,
            files=None,
        )

    ref[0] = 1.0
    parsed = runner.parse_manifest_arguments(["--special"])
    runner.run(
        "special",
        base_dir,
        manifest_args=parsed,
        reporters=reporters,
        options=options,
        files=None,
    )
    assert math.isclose(ref[0], 8.0)
    assert not reporters.has_error()

    ref[0] = 1.0
    parsed = runner.parse_manifest_arguments(["--num", "1", "--special"])
    runner.run(
        "special",
        base_dir,
        manifest_args=parsed,
        reporters=reporters,
        options=options,
        files=None,
    )
    assert math.isclose(ref[0], 4.0)
    assert not reporters.has_error()

    manifest = fake_manifest_with_options(base_dir, None, num_required=True, ref=ref)
    runner = Runner(manifest)

    ref[0] = 1.0
    parsed = runner.parse_manifest_arguments(["--num", "1"])
    runner.run(
        "op1",
        base_dir,
        manifest_args=parsed,
        reporters=reporters,
        options=options,
        files=None,
    )
    assert math.isclose(ref[0], 3.0)
    assert not reporters.has_error()

    ref[0] = 1.0
    parsed = runner.parse_manifest_arguments(["--num", "2"])
    runner.run(
        "op1",
        base_dir,
        manifest_args=parsed,
        reporters=reporters,
        options=options,
        files=None,
    )
    assert math.isclose(ref[0], 30.0)
    assert not reporters.has_error()


class ValidCommand(CommandBase):
    @property
    def name(self) -> str:
        return "valid"

    def __call__(self, reporter: Reporter) -> int:
        return 0


class InvalidCommand(CommandBase):
    @property
    def name(self) -> str:
        return "my:py"

    def __call__(self, reporter: Reporter) -> int:
        return 0


def test__verify_command_name() -> None:
    _verify_command_name(ValidCommand())
    with pytest.raises(InvalidCommandNameError):
        _verify_command_name(InvalidCommand())


class MockCommand(CommandBase):
    @property
    def name(self) -> str:
        "mock"

    def __call__(self, reporter: Reporter) -> int:
        return 0

    @property
    def has_side_effects(self) -> bool:
        return True


class PurelyFunctionalCommand(CommandBase):
    @property
    def name(self) -> str:
        "preferred_command"

    def __call__(self, reporter: Reporter) -> int:
        return 0

    @property
    def has_side_effects(self) -> bool:
        return False


def test__has_side_effects() -> None:
    pfc = PurelyFunctionalCommand()
    mc = MockCommand()
    assert _has_side_effects([pfc, pfc, pfc, mc])
    assert _has_side_effects([mc, mc, mc, mc])
    assert not _has_side_effects([pfc, pfc, pfc, pfc])
