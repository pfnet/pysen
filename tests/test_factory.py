from pysen.black import Black
from pysen.factory import ConfigureLintOptions, configure_lint
from pysen.source import Source


def test_configure_lint_default_source() -> None:
    components = configure_lint(ConfigureLintOptions(enable_black=True, source=None))
    assert len(components) == 1
    black = components[0]
    assert isinstance(black, Black)
    source = black.source
    assert isinstance(source, Source)
    assert source.includes.keys() == {"."}
