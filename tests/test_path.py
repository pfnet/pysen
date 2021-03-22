import pathlib

from pysen.path import change_dir, get_relative_path, is_contained, is_covered

BASE_DIR = pathlib.Path(__file__).resolve().parent


def test_get_relative_path() -> None:
    base_dir = pathlib.Path("/opt/pysen/python/packages")
    assert get_relative_path("foo/A", base_dir) == "foo/A"
    assert get_relative_path(pathlib.Path("foo/A"), base_dir) == "foo/A"

    assert get_relative_path("../foo/B", base_dir) == "../foo/B"
    assert get_relative_path(pathlib.Path("../foo/B"), base_dir) == "../foo/B"

    assert get_relative_path("/opt/pysen/C", base_dir) == "../../C"
    assert get_relative_path(pathlib.Path("/opt/pysen/C"), base_dir) == "../../C"

    assert get_relative_path("/opt/pysen/python2/D", base_dir) == "../../python2/D"
    assert (
        get_relative_path("/opt/pysen/python/packages/configs/E", base_dir)
        == "configs/E"
    )
    assert (
        get_relative_path("/home/user/.config/F", base_dir)
        == "../../../../home/user/.config/F"
    )


def test_change_dir() -> None:
    current = pathlib.Path.cwd()

    with change_dir(BASE_DIR / "fakes"):
        assert pathlib.Path.cwd() == BASE_DIR / "fakes"

    assert pathlib.Path.cwd() == current


def test_is_covered() -> None:
    hoge = pathlib.Path("hoge")
    bar = pathlib.Path("bar")
    assert is_covered(hoge, [hoge])
    assert is_covered(hoge, [hoge, bar])
    assert is_covered(hoge / "foo", [hoge])
    assert is_covered(hoge / "foo" / "bar", [hoge])

    assert not is_covered(hoge, [])
    assert not is_covered(hoge, [bar])
    assert not is_covered(hoge, [hoge / "subdir"])


def test_is_contained() -> None:
    foo = pathlib.Path("foo").resolve()
    bar = pathlib.Path("bar")
    baz = pathlib.Path("baz")
    ufoo = pathlib.Path("~/foo").resolve()
    ufooo = pathlib.Path("~/foo").expanduser().resolve()

    assert not is_contained(foo / bar, foo)
    assert not is_contained(foo / bar, foo / baz / bar)
    assert is_contained(foo, foo / bar)
    assert is_contained(foo / bar, foo / bar / baz)

    # user expansion not supported
    assert not is_contained(ufoo, ufooo)
