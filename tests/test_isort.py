from pathlib import Path
from unittest import mock

import pkg_resources
import pytest

from pysen.exceptions import (
    DistributionNotFound,
    IncompatibleVersionError,
    UnexpectedErrorFormat,
)
from pysen.ext.isort_wrapper import (
    IsortSectionName,
    IsortSetting,
    _check_version_compatibility,
    _get_isort_version,
    _parse_file_path,
)
from pysen.py_version import VersionRepresentation


def test_export() -> None:
    setting = IsortSetting(
        known_third_party={"alpha", "beta"},
        default_section=IsortSectionName.THIRDPARTY,
        sections=[IsortSectionName.FUTURE, IsortSectionName.STDLIB],
        force_single_line=True,
        line_length=80,
    )

    name, section = setting.export()
    assert name == ["tool", "isort"]

    assert section == {
        "known_third_party": ["alpha", "beta"],
        "default_section": "THIRDPARTY",
        "sections": ["FUTURE", "STDLIB"],
        "line_length": 80,
        "force_single_line": True,
        # NOTE(igarashi): the following values are emitted by default
        "force_grid_wrap": 0,
        "include_trailing_comma": True,
        "multi_line_output": 3,
        "use_parentheses": True,
    }


def test_to_black_compatible() -> None:
    setting = IsortSetting(
        force_single_line=False,
        include_trailing_comma=False,
        multi_line_output=1,
        ensure_newline_before_comments=False,
        force_grid_wrap=1,
        use_parentheses=False,
    )
    with mock.patch(
        "pysen.ext.isort_wrapper._get_isort_version",
        return_value=VersionRepresentation(5, 0, 0),
    ):
        black_compat = setting.to_black_compatible()
    assert black_compat.multi_line_output == 3
    assert black_compat.include_trailing_comma
    assert black_compat.force_grid_wrap == 0
    assert black_compat.use_parentheses
    assert black_compat.ensure_newline_before_comments


def test__check_version_compatibility() -> None:
    with pytest.raises(IncompatibleVersionError):
        _check_version_compatibility(True, VersionRepresentation(4, 0))
    with pytest.raises(IncompatibleVersionError):
        _check_version_compatibility(False, VersionRepresentation(4, 0))
    _check_version_compatibility(None, VersionRepresentation(4, 0))
    _check_version_compatibility(True, VersionRepresentation(5, 0))
    _check_version_compatibility(False, VersionRepresentation(5, 0))
    _check_version_compatibility(None, VersionRepresentation(5, 0))


def test__parse_file_path() -> None:
    isort_format_before = (
        "/path/to/error_line_parser.py:before      2020-06-01 16:18:40.123155"
    )
    isort_format_after = (
        "/path/to/error_line_parser.py:after      2020-06-01 16:18:40.123155"
    )
    isort_format_invalid = (
        "/path/to/error_line_parser.py      2020-06-01 16:18:40.123155"
    )

    assert _parse_file_path(isort_format_before) == Path(
        "/path/to/error_line_parser.py"
    )
    assert _parse_file_path(isort_format_after) == Path("/path/to/error_line_parser.py")
    with pytest.raises(UnexpectedErrorFormat):
        _parse_file_path(isort_format_invalid)


def test__get_isort_version() -> None:
    def get_version() -> VersionRepresentation:
        _get_isort_version.cache_clear()
        return _get_isort_version()

    distro = "pkg_resources.get_distribution"
    # pass case
    with mock.patch(distro, return_value=mock.Mock(version="4.3.21")):
        assert get_version() == VersionRepresentation(4, 3, 21)
    with mock.patch(distro, return_value=mock.Mock(version="5.1.2")):
        assert get_version() == VersionRepresentation(5, 1, 2)
    # incompatible version
    with pytest.raises(IncompatibleVersionError) as e:
        with mock.patch(distro, return_value=mock.Mock(version="3.0.0")):
            get_version()
    assert "version 3.0.0 is not supported" in str(e)
    # isort cannot be imported
    with pytest.raises(DistributionNotFound) as e:
        with mock.patch(
            distro, side_effect=pkg_resources.DistributionNotFound("req", "requires")
        ):
            get_version()
    assert "Expected isort to be installed" in str(e)
