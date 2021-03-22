import pathlib
import sys

import pytest

from pysen.py_module import _parse_entry_point, load

CURRENT_FILE = pathlib.Path(__file__).resolve()
BASE_DIR = CURRENT_FILE.parent


def test__parse_entry_point() -> None:
    assert _parse_entry_point("hoge") is None
    assert _parse_entry_point("hoge.fuga") is None
    assert _parse_entry_point("hoge.fuga::piyo") == ("hoge.fuga", "piyo")
    assert _parse_entry_point("hoge::piyo") == ("hoge", "piyo")
    assert _parse_entry_point("::piyo") is None
    assert _parse_entry_point("1::piyo") is None
    assert _parse_entry_point("hoge::2") is None
    assert _parse_entry_point("_hoge1._fuga2_::_piyo3_") == (
        "_hoge1._fuga2_",
        "_piyo3_",
    )
    assert _parse_entry_point("hoge::piyo\nfuga") is None


def test_load() -> None:
    with pytest.raises(FileNotFoundError):
        load(BASE_DIR / "hoge", "builder")

    with pytest.raises(FileNotFoundError):
        load(BASE_DIR, "builder")

    module = load(BASE_DIR / "fakes/configs/good_builder.py", "foo")
    assert module is not None
    assert getattr(module, "build") is not None  # NOQA: B009
    assert module.__name__.startswith("pysen._modules.foo_")
    assert sys.modules[module.__name__]

    module = load(BASE_DIR / "fakes/configs/invalid_interface_builder.py", "bar")
    assert module is not None
    assert getattr(module, "build2") is not None  # NOQA: B009
    assert module.__name__.startswith("pysen._modules.bar_")
    assert sys.modules[module.__name__]

    module2 = load(BASE_DIR / "fakes/configs/invalid_return_builder.py", "foo")
    assert module2 is not None
    assert getattr(module2, "build") is not None  # NOQA: B009
    assert sys.modules[module2.__name__]
    assert module2.__name__ != module.__name__

    # NOTE(igarashi): py_module.load currently raises the error that a loading module
    # raises as is. It might be better to wrap the exception with our custom error type
    # so that the one can know the error is from a module.
    with pytest.raises(BufferError):
        load(BASE_DIR / "fakes/configs/error_builder.py", "builder")
