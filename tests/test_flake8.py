from typing import Any, Dict

from pysen.ext.flake8_wrapper import Flake8Setting


def test_flake8_setting_comment() -> None:
    flake8 = Flake8Setting().to_black_compatible()
    assert len(flake8._comments) > 0
    section_name, section = flake8.export()
    assert section_name == ["flake8"]
    comments: Dict[str, Any] = {k: v for k, v in section.items() if k.startswith("#")}
    assert len(comments) > 0
    # check that each comment entry doesn't have a value
    assert all(x is None for x in comments.values())
