import argparse
import pathlib
import tempfile
import unittest.mock
from typing import Optional, Sequence

import pytest

import pysen
from pysen import ConfigureLintOptions, configure_lint
from pysen.exceptions import CommandNotFoundError
from pysen.manifest import Manifest, TargetType
from pysen.reporter import ReporterFactory
from pysen.runner_options import RunOptions

BASE_DIR = pathlib.Path(__file__).resolve().parent


def test_load_manifest() -> None:
    manifest = pysen.load_manifest(BASE_DIR / "fakes/configs/example.toml")
    assert manifest is not None

    with pytest.raises(FileNotFoundError):
        pysen.load_manifest(BASE_DIR / "no_such_file.toml")


def test_build_manifest() -> None:
    # NOTE(igarashi): since build_manifest is just a reference for pysen.build_manifest.build,
    # we just check if the function does not raise an error in this test.
    manifest = pysen.build_manifest(
        [], external_builder=BASE_DIR / "fakes/configs/good_builder.py"
    )
    assert manifest is not None


def test_run() -> None:
    with unittest.mock.patch(
        "pysen.runner.Runner.export_settings"
    ) as mock_export, unittest.mock.patch("pysen.runner.run_target") as mock_run:
        assert pysen.run(
            BASE_DIR, "lint", pyproject=BASE_DIR / "fakes/configs/example.toml"
        )
        mock_export.assert_called()

        # check if settings_dir is correctly handled
        mock_export.reset_mock()
        with tempfile.TemporaryDirectory() as d:
            td = pathlib.Path(d)
            assert pysen.run(
                BASE_DIR,
                "lint",
                pyproject=BASE_DIR / "fakes/configs/example.toml",
                settings_dir=td,
            )
            mock_export.assert_called_once_with(
                BASE_DIR, td, argparse.Namespace(disable=None, enable=None)
            )

        with pytest.raises(CommandNotFoundError):
            assert pysen.run(
                BASE_DIR, "lint2", pyproject=BASE_DIR / "fakes/configs/example.toml"
            )

        components = configure_lint(ConfigureLintOptions(enable_black=True))
        assert pysen.run(BASE_DIR, "lint", components=components)
        with pytest.raises(CommandNotFoundError):
            assert pysen.run(BASE_DIR, "lint2", components=components)

        manifest = Manifest(components)
        assert pysen.run(BASE_DIR, "lint", manifest=manifest)
        with pytest.raises(CommandNotFoundError):
            assert pysen.run(BASE_DIR, "lint2", manifest=manifest)

        # TODO(igarashi): Add test to check run() handles both args and manifest_args

        with pytest.raises(FileNotFoundError):
            pysen.run(BASE_DIR, "lint", pyproject=BASE_DIR / "no_such_file.toml")

        with pytest.raises(ValueError):
            pysen.run(BASE_DIR, "lint")

        with pytest.raises(ValueError):
            pysen.run(
                BASE_DIR,
                "lint",
                pyproject=BASE_DIR / "fakes/configs/example.toml",
                manifest=manifest,
            )

        # NOTE(igarashi): Check that run() returns False when the command reports an error

        def side_effect(
            target: TargetType,
            reporters: ReporterFactory,
            options: RunOptions,
            files: Optional[Sequence[pathlib.Path]],
        ) -> None:
            with reporters.create("hoge") as r:
                r.set_result(False, 128)

        mock_run.side_effect = side_effect

        assert not pysen.run(
            BASE_DIR, "lint", pyproject=BASE_DIR / "fakes/configs/example.toml"
        )
        assert not pysen.run(BASE_DIR, "lint", components=components)
        assert not pysen.run(BASE_DIR, "lint", manifest=manifest)
