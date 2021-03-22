import pathlib
import subprocess

import pytest

from pysen.path import change_dir

TARGET_EXAMPLE = "plugin_example"


@pytest.mark.examples
def test_cli_run(example_dir: pathlib.Path) -> None:
    target = example_dir / TARGET_EXAMPLE
    with change_dir(target):
        subprocess.run(["pysen", "run", "lint"], check=True)
        subprocess.run(["pysen", "run", "hook"])
        subprocess.run(["pysen", "--ignore-lint", "run", "lint"], check=True)
        subprocess.run(["pysen", "--ignore-lint", "run", "hook"], check=True)
        subprocess.run(["pysen", "run", "--error-format", "gnu", "lint"], check=True)
