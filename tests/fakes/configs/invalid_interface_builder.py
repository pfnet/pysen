import pathlib
from typing import Optional, Sequence

from pysen import ComponentBase, Manifest, ManifestBase, Source, factory


def build2(
    components: Sequence[ComponentBase], src_path: Optional[pathlib.Path]
) -> ManifestBase:
    assert src_path is not None
    components = factory.configure_lint(
        factory.ConfigureLintOptions(
            enable_flake8=True,
            enable_isort=True,
            source=Source(includes=[src_path.resolve().parent]),
        )
    )
    return Manifest(components)
