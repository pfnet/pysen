import pathlib
from typing import Optional, Sequence

from pysen import ComponentBase, Manifest, ManifestBase, Source, factory
from pysen.black import Black


def build(
    components: Sequence[ComponentBase], src_path: Optional[pathlib.Path]
) -> ManifestBase:
    black = next((x for x in components if isinstance(x, Black)), None)
    source: Source

    if black is not None:
        source = black.source
    else:
        src_path = src_path or pathlib.Path.cwd()
        source = Source(includes=[src_path.resolve().parent])

    components = factory.configure_lint(
        factory.ConfigureLintOptions(
            enable_flake8=True,
            enable_isort=True,
            source=source,
        )
    )
    return Manifest(components)
