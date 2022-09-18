import pathlib
import subprocess

import pytest
from setuptools import sandbox

from pysen.path import change_dir

TARGET_EXAMPLE = "sync_cmdclass_pyproject"


@pytest.mark.examples
def test_cli_run(example_dir: pathlib.Path) -> None:
    target = example_dir / TARGET_EXAMPLE
    with change_dir(target):
        subprocess.run(["pysen", "run", "lint"], check=True)
        subprocess.run(["pysen", "run", "format"], check=True)
        subprocess.run(["pysen", "run", "--error-format", "gnu", "lint"], check=True)


@pytest.mark.examples
def test_setuptools_cli(example_dir: pathlib.Path) -> None:
    target = example_dir / TARGET_EXAMPLE
    setup_py = target / "setup.py"
    assert setup_py.exists()

    subprocess.run(["python", str(setup_py), "lint"], check=True)


@pytest.mark.xfail
def test_setuptools_sandbox(example_dir: pathlib.Path) -> None:
    target = example_dir / TARGET_EXAMPLE
    setup_py = target / "setup.py"
    assert setup_py.exists()

    sandbox.run_setup(str(setup_py), ["lint"])  # type: ignore
