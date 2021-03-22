import pathlib
import tempfile
from typing import List

import pytest

from pysen import ManifestBase
from pysen.black import Black
from pysen.component import ComponentBase
from pysen.exceptions import InvalidManifestBuilderError
from pysen.flake8 import Flake8
from pysen.manifest import Manifest
from pysen.manifest_builder import _build, _build_external, build
from pysen.source import Source

CURRENT_FILE = pathlib.Path(__file__).resolve()
BASE_DIR = CURRENT_FILE.parent


def get_source_from_good_builder(manifest: ManifestBase) -> Source:
    assert isinstance(manifest, Manifest)
    flake8 = manifest.get_component("flake8")
    assert isinstance(flake8, Flake8)
    return flake8.source


def test__build_external() -> None:
    manifest = _build_external(
        BASE_DIR / "fakes/configs/good_builder.py", [], CURRENT_FILE
    )
    assert get_source_from_good_builder(manifest).includes.keys() == {BASE_DIR}

    test_source = Source(includes=["/hoge/fuga"])
    manifest = _build_external(
        BASE_DIR / "fakes/configs/good_builder.py",
        [Black(source=test_source)],
        CURRENT_FILE,
    )
    assert get_source_from_good_builder(manifest) == test_source

    with tempfile.TemporaryDirectory() as d:
        tempdir = pathlib.Path(d)
        manifest = _build_external(
            BASE_DIR / "fakes/configs/good_builder.py", [], tempdir / "hoge"
        )
        assert get_source_from_good_builder(manifest).includes.keys() == {tempdir}

    with pytest.raises(InvalidManifestBuilderError) as ex:
        _build_external(
            BASE_DIR / "fakes/configs/invalid_interface_builder.py", [], CURRENT_FILE
        )

    assert "external builder must have" in str(ex.value)

    with pytest.raises(InvalidManifestBuilderError) as ex:
        _build_external(
            BASE_DIR / "fakes/configs/invalid_return_builder.py", [], CURRENT_FILE
        )

    assert "instance of ManifestBase" in str(ex.value)


def test__build() -> None:
    manifest = _build([], CURRENT_FILE)
    assert isinstance(manifest, Manifest)
    assert len(manifest.components) == 0

    black = Black()
    manifest = _build([black], CURRENT_FILE)
    assert isinstance(manifest, Manifest)
    assert manifest.components == [black]


def test_build() -> None:
    test_source = Source(includes=["/hoge/fuga"])
    test_components: List[ComponentBase] = [Black(source=test_source)]

    manifest = build(test_components, CURRENT_FILE)
    assert isinstance(manifest, Manifest)
    assert manifest.components == test_components

    manifest = build(
        [],
        CURRENT_FILE,
        external_builder=BASE_DIR / "fakes/configs/good_builder.py",
    )
    assert isinstance(manifest, Manifest)
    assert len(manifest.components) == 2
    assert get_source_from_good_builder(manifest).includes.keys() == {BASE_DIR}

    manifest = build(
        test_components,
        CURRENT_FILE,
        external_builder=BASE_DIR / "fakes/configs/good_builder.py",
    )
    assert isinstance(manifest, Manifest)
    assert len(manifest.components) == 2
    assert get_source_from_good_builder(manifest) == test_source
