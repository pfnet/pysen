import argparse
import pathlib
from typing import Any, Callable, Dict, List, Optional, Sequence

import pytest

from fakes.component import FakeComponent, Operation
from pysen import dumper
from pysen.component import ComponentBase
from pysen.exceptions import InvalidComponentName
from pysen.manifest import Manifest, export_settings, get_target, get_targets
from pysen.runner_options import PathContext, RunOptions
from pysen.setting import SettingFile

FixtureType = Callable[..., Sequence[ComponentBase]]


@pytest.fixture
def fake_components() -> FixtureType:
    def create(
        base_dir: Optional[pathlib.Path],
        settings_dir: Optional[pathlib.Path],
        ref: Optional[List[float]] = None,
    ) -> Sequence[ComponentBase]:
        r = ref or [1.0]
        return (
            FakeComponent(
                "node1",
                {"op1": (2, Operation.MUL), "op2": (10, Operation.ADD)},
                base_dir,
                settings_dir,
                r,
            ),
            FakeComponent(
                "node2",
                {"op1": (3, Operation.MUL), "op3": (-1, Operation.MUL)},
                base_dir,
                settings_dir,
                r,
            ),
        )

    return create


def test_components(fake_components: FixtureType) -> None:
    components = fake_components(pathlib.Path(), pathlib.Path())
    c = Manifest(components)
    assert c.components == list(components)


def test_default_dump_handler() -> None:
    m = Manifest()
    assert m._dump_handler == dumper.dump


def test_export_settings(fake_components: FixtureType) -> None:
    base_dir = pathlib.Path("/foo/bar")
    settings_dir = pathlib.Path("/settings")
    paths = PathContext(base_dir, settings_dir)
    components = fake_components(base_dir, settings_dir)

    dumped: Dict[str, Dict[str, Any]] = {}

    def dump(s_dir: pathlib.Path, fname: str, data: SettingFile) -> None:
        assert s_dir == settings_dir
        dumped[fname] = data.as_dict()

    export_settings(paths, components, dump)
    assert len(dumped.keys()) == 3
    expected = {
        "op1.yaml": {"node1": {"coef": 2, "op": "*"}, "node2": {"coef": 3, "op": "*"}},
        "op2.yaml": {"node1": {"coef": 10, "op": "+"}},
        "op3.yaml": {"node2": {"coef": -1, "op": "*"}},
    }
    assert expected == dumped
    dumped.clear()

    m = Manifest(components, dump_handler=dump)
    m.export_settings(paths, argparse.Namespace(enable=None, disable=None))
    assert len(dumped.keys()) == 3
    expected = {
        "op1.yaml": {"node1": {"coef": 2, "op": "*"}, "node2": {"coef": 3, "op": "*"}},
        "op2.yaml": {"node1": {"coef": 10, "op": "+"}},
        "op3.yaml": {"node2": {"coef": -1, "op": "*"}},
    }
    assert expected == dumped

    dumped.clear()
    # NOTE(igarashi): export_settings intentionally ignores enable and disable arguments.
    # See manifest.py for more details
    m.export_settings(paths, argparse.Namespace(enable=["node1"], disable=None))
    assert len(dumped.keys()) == 3
    expected = {
        "op1.yaml": {"node1": {"coef": 2, "op": "*"}, "node2": {"coef": 3, "op": "*"}},
        "op2.yaml": {"node1": {"coef": 10, "op": "+"}},
        "op3.yaml": {"node2": {"coef": -1, "op": "*"}},
    }
    assert expected == dumped


def test_get_targets(fake_components: FixtureType) -> None:
    components = fake_components(None, None)

    targets = get_targets(components)
    assert targets == {"op1": ["node1", "node2"], "op2": ["node1"], "op3": ["node2"]}

    m = Manifest(components)
    targets = m.get_targets(argparse.Namespace(enable=None, disable=None))
    assert targets == {"op1": ["node1", "node2"], "op2": ["node1"], "op3": ["node2"]}

    targets = m.get_targets(argparse.Namespace(enable=None, disable=["node1"]))
    assert targets == {"op1": ["node2"], "op3": ["node2"]}

    targets = m.get_targets(argparse.Namespace(enable=["node1"], disable=None))
    assert targets == {"op1": ["node1"], "op2": ["node1"]}

    with pytest.raises(InvalidComponentName) as e:
        m.get_targets(argparse.Namespace(enable=["noexist", "ditto"], disable=None))
    assert (
        "The following component(s) in option --enable were not found: ditto,noexist"
        in str(e)
    )
    with pytest.raises(InvalidComponentName) as e:
        m.get_targets(argparse.Namespace(disable=["ditto"], enable=None))
    assert (
        "The following component(s) in option --disable were not found: ditto" in str(e)
    )


def test_get_target(fake_components: FixtureType) -> None:
    base_dir = pathlib.Path("/foo/bar")
    settings_dir = pathlib.Path("/settings")
    paths = PathContext(base_dir, settings_dir)
    options = RunOptions()
    components = fake_components(base_dir, settings_dir)

    target = get_target("op1", components, paths, options)
    assert len(target) == 2
    assert {target[0].name, target[1].name} == {"* 2", "* 3"}

    assert get_target("op99", components, paths, options) == []

    m = Manifest(components)

    # expected to be same as get_target("op1", component, base_dir)
    target = m.get_target(
        "op1", paths, options, argparse.Namespace(enable=None, disable=None)
    )
    assert len(target) == 2
    assert {target[0].name, target[1].name} == {"* 2", "* 3"}

    target = m.get_target(
        "op2", paths, options, argparse.Namespace(enable=None, disable=None)
    )
    assert len(target) == 1
    assert {target[0].name} == {"+ 10"}

    assert (
        m.get_target(
            "op99", paths, options, argparse.Namespace(enable=None, disable=None)
        )
        == []
    )

    # check if components are filtered by disable option
    target = m.get_target(
        "op1", paths, options, argparse.Namespace(enable=None, disable=["node1"])
    )
    assert len(target) == 1
    assert {target[0].name} == {"* 3"}

    assert (
        m.get_target(
            "op2", paths, options, argparse.Namespace(enable=None, disable=["node1"])
        )
        == []
    )

    target = m.get_target(
        "op3", paths, options, argparse.Namespace(enable=None, disable=["node1"])
    )
    assert len(target) == 1
    assert target[0].name == "* -1"
