import pytest
import tomlkit

from pysen.setting import _create_dict, _traverse_toml


def test__create_dict() -> None:
    assert _create_dict([]) == {}
    assert _create_dict(["foo"]) == {"foo": {}}
    assert _create_dict(["foo", "bar"]) == {"foo": {"bar": {}}}
    assert _create_dict(["foo", "bar", "baz"]) == {"foo": {"bar": {"baz": {}}}}


def test__traverse_toml() -> None:
    unordered_document = """
    [tool.poetry]
    hoo=1
    [build-system]
    foo=42
    [tool.pysen-cli]
    bar=43
    """
    document = tomlkit.loads(unordered_document)
    tool = document["tool"]
    # OutOfOrderTableProxy is problematic as it is a reference and cannot be traversed.
    assert isinstance(tool, tomlkit.container.OutOfOrderTableProxy)
    tool["hoge"] = {}
    with pytest.raises(tomlkit.exceptions.NonExistentKey):
        tool["hoge"]
    with pytest.raises(ValueError):
        _traverse_toml(("tool", "hoge", "answer"), document, False)
    _traverse_toml(("tool", "hoge", "answer"), document, True)
    assert document["tool"]["hoge"]["answer"] == {}
