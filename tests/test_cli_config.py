import pathlib

from pysen.cli_config import parse

BASE_DIR = pathlib.Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "fakes/configs"


def test_example() -> None:
    config = parse(CONFIG_DIR / "example.toml")
    assert config is not None
    assert config.settings_dir is not None
    assert config.settings_dir == CONFIG_DIR / "hoge"
    assert config.settings_dir.is_absolute()


def test_parse() -> None:
    assert parse(CONFIG_DIR / "example.toml") is not None
    assert parse(CONFIG_DIR / "simple_source.toml") is None
