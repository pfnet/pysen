import pathlib

import pytest

from pysen.plugin import PluginBase
from pysen.plugin_loader import load_from_file, load_from_module, load_plugin
from pysen.pyproject_model import Config, PluginConfig

CURRENT_FILE = pathlib.Path(__file__).resolve()
BASE_DIR = CURRENT_FILE.parent


def test_load_from_file() -> None:
    root = Config()
    config = PluginConfig(
        location="tool.pysen.plugin.hoge", script=BASE_DIR / "fakes/plugin.py"
    )

    plugin = load_from_file(BASE_DIR / "fakes/plugin.py")
    assert isinstance(plugin, PluginBase)
    components = plugin.load(CURRENT_FILE, config, root)
    assert len(components) == 0

    config.config = {"enable_c1": True}
    components = plugin.load(CURRENT_FILE, config, root)
    assert len(components) == 1
    assert components[0].name == "plugin_component1"


def test_load_from_module() -> None:
    root = Config()
    config = PluginConfig(
        location="tool.pysen.plugin.hoge", function="fakes.plugin::plugin"
    )

    plugin = load_from_module("fakes.plugin::plugin")
    assert isinstance(plugin, PluginBase)
    components = plugin.load(CURRENT_FILE, config, root)
    assert len(components) == 0

    plugin = load_from_module("fakes.plugin::create")
    assert isinstance(plugin, PluginBase)
    components = plugin.load(CURRENT_FILE, config, root)
    assert len(components) == 0

    config.config = {"enable_c2": True}
    components = plugin.load(CURRENT_FILE, config, root)
    assert len(components) == 1
    assert components[0].name == "create_component2"


def test_load_plugin() -> None:
    def assert_plugin_entry_point(plugin: PluginBase, entry_point: str) -> None:
        root = Config()
        config = PluginConfig(
            location="tool.pysen.plugin.hoge", config={"enable_c1": True}
        )
        components = plugin.load(CURRENT_FILE, config, root)
        assert len(components) == 1
        assert components[0].name == f"{entry_point}_component1"

    plugin = load_plugin(function="fakes.plugin::create")
    assert isinstance(plugin, PluginBase)
    assert_plugin_entry_point(plugin, "create")

    plugin = load_plugin(script=BASE_DIR / "fakes/plugin.py")
    assert isinstance(plugin, PluginBase)
    assert_plugin_entry_point(plugin, "plugin")

    with pytest.raises(TypeError):
        load_plugin(
            function="fakes.plugin::unknown", script=BASE_DIR / "fakes/plugin.py"
        )

    with pytest.raises(TypeError):
        load_plugin()
