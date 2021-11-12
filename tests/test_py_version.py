import pytest

from pysen.py_version import PythonVersion, VersionRepresentation


def test_python_version() -> None:
    py36 = PythonVersion(3, 6)

    assert py36 == PythonVersion(3, 6)
    assert py36 != PythonVersion(3, 7)

    assert py36.version == "3.6"
    assert py36.full_representation == "Python3.6"
    assert py36.short_representation == "py36"

    py368 = PythonVersion(3, 6, 8)

    assert py368 == PythonVersion(3, 6, 8)
    assert py368 != PythonVersion(3, 6, 9)
    assert py368 != py36

    assert py368.version == "3.6.8"
    assert py368.full_representation == "Python3.6.8"
    assert py368.short_representation == "py36"


def test_version_ops() -> None:
    assert VersionRepresentation(3, 6) == VersionRepresentation(3, 6, None, None)
    with pytest.raises(NotImplementedError):
        assert VersionRepresentation(3, 6) == "3"


def test_version_comp() -> None:
    def assert_rhs_is_larger(
        lhs: VersionRepresentation, rhs: VersionRepresentation
    ) -> None:
        assert lhs < rhs
        assert not rhs < lhs

    assert_rhs_is_larger(VersionRepresentation(0, 4, 5), VersionRepresentation(1, 2, 3))
    assert_rhs_is_larger(VersionRepresentation(1, 0), VersionRepresentation(2, 0))
    assert_rhs_is_larger(VersionRepresentation(0, 5), VersionRepresentation(0, 6))
    assert_rhs_is_larger(VersionRepresentation(0, 5), VersionRepresentation(0, 5, 1))

    assert not VersionRepresentation(0, 5, 1, "b0") < VersionRepresentation(
        0, 5, 1, "b1"
    )
    assert not VersionRepresentation(0, 5, 1, "b1") < VersionRepresentation(
        0, 5, 1, "b0"
    )


def test_is_compatible() -> None:
    assert VersionRepresentation(0, 5).is_compatible(VersionRepresentation(0, 5))
    assert VersionRepresentation(0, 5).is_compatible(VersionRepresentation(0, 5, 7))
    assert VersionRepresentation(0, 5).is_compatible(VersionRepresentation(0, 5, 1))
    assert VersionRepresentation(0, 5, 5).is_compatible(VersionRepresentation(0, 5, 4))
    assert VersionRepresentation(0, 5, 5).is_compatible(VersionRepresentation(0, 5, 6))
    assert VersionRepresentation(3, 6).is_compatible(VersionRepresentation(3, 6))
    assert not VersionRepresentation(3, 6).is_compatible(VersionRepresentation(3, 5))
    assert not VersionRepresentation(3, 6, 8).is_compatible(
        VersionRepresentation(3, 5, 32)
    )
    assert not VersionRepresentation(2, 6).is_compatible(VersionRepresentation(3, 0))
    assert not VersionRepresentation(4, 6).is_compatible(VersionRepresentation(3, 0))


def test_version_from_str() -> None:
    def check_version(s: str, expected: VersionRepresentation) -> None:
        actual = VersionRepresentation.from_str(s)
        assert actual == expected
        assert s == str(expected)

    cases = {
        ("0.601", VersionRepresentation(0, 601)),
        ("3.0.8", VersionRepresentation(3, 0, 8)),
        ("3.6.8a1", VersionRepresentation(3, 6, 8, "a1")),
        ("3.6a1", VersionRepresentation(3, 6, None, "a1")),
        ("3.6b0", VersionRepresentation(3, 6, None, "b0")),
        ("3.6rc993", VersionRepresentation(3, 6, None, "rc993")),
    }
    for case in cases:
        check_version(*case)

    with pytest.raises(ValueError):
        # prelease phase must be either a, b, or rc
        VersionRepresentation.from_str("3.6.8alpha1")
    with pytest.raises(ValueError):
        # MUST have a pre-release number
        VersionRepresentation.from_str("3.6.8a")
    with pytest.raises(ValueError):
        # MUST NOT start with zero followed by another number
        VersionRepresentation.from_str("03.1")
    with pytest.raises(ValueError):
        # MUST NOT start with zero followed by another number
        VersionRepresentation.from_str("00.1")
    with pytest.raises(ValueError):
        # MUST have minor
        VersionRepresentation.from_str("3")
    with pytest.raises(ValueError):
        # too many dots
        VersionRepresentation.from_str("3.0.100.1")
    with pytest.raises(ValueError):
        VersionRepresentation.from_str("3.")
