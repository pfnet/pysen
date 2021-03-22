import pathlib

import pytest

BASE_DIR = pathlib.Path(__file__).resolve().parent


@pytest.fixture
def example_dir() -> pathlib.Path:
    ret = BASE_DIR.parents[1] / "examples"
    assert ret.exists()
    return ret
