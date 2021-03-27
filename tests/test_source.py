import contextlib
import pathlib
import tempfile
from typing import Iterator, Set

import git
import pytest
import tomlkit

from pysen.path import change_dir
from pysen.source import (
    PythonFileFilter,
    Source,
    SourceEntrySetting,
    _resolve,
    extension_filter,
)

BASE_DIR = pathlib.Path(__file__).resolve().parent


def test__resolve() -> None:
    current_file = pathlib.Path(__file__)
    setting = SourceEntrySetting(glob=False)
    assert _resolve(BASE_DIR, current_file.name, setting) == [current_file.absolute()]
    assert _resolve(BASE_DIR, current_file.absolute(), setting) == [
        current_file.absolute()
    ]
    assert _resolve(BASE_DIR, str(current_file.name), setting) == [
        current_file.absolute()
    ]
    assert _resolve(BASE_DIR, str(current_file.absolute()), setting) == [
        current_file.absolute()
    ]

    override_base = pathlib.Path("/opt/pysen")
    setting = SourceEntrySetting(glob=False, base_dir=override_base)
    assert _resolve(BASE_DIR, current_file.name, setting) == [
        override_base / current_file.name
    ]
    assert _resolve(BASE_DIR, current_file.absolute(), setting) == [
        current_file.absolute()
    ]
    assert _resolve(BASE_DIR, str(current_file.name), setting) == [
        override_base / current_file.name
    ]
    assert _resolve(BASE_DIR, str(current_file.absolute()), setting) == [
        current_file.absolute()
    ]

    setting = SourceEntrySetting(glob=True)

    with pytest.raises(RuntimeError):
        _resolve(BASE_DIR, pathlib.Path("**/*"), setting)

    resolved = _resolve(BASE_DIR, "**/*.py", setting)
    assert len(resolved) > 1
    assert all(str(x).startswith(str(BASE_DIR)) and x.suffix == ".py" for x in resolved)

    # NOTE(igarashi): check base_dir of glob is overridden by setting
    setting = SourceEntrySetting(glob=True, base_dir=BASE_DIR / "fakes")
    resolved_with_base = _resolve(BASE_DIR, "**/*.py", setting)
    assert len(resolved_with_base) > 1
    assert len(resolved) > len(resolved_with_base)
    assert all(
        str(x).startswith(str(BASE_DIR / "fakes")) and x.suffix == ".py"
        for x in resolved_with_base
    )

    # test if _resolve doesn't raise an error though we specify an invalid pattern
    resolved = _resolve(BASE_DIR, "hoge!%&#'/+*hoge", setting)
    assert len(resolved) == 0

    # Test if _resolve doesn't raise an error though we use a string-like object.
    # This case is intended to check that _resolve converts a string-like object
    # to the Python string object since pathlib.glob(x) now raises an error
    # if x is not a Python string object due to sys.intern(x).
    str_like = tomlkit.item("build")
    assert isinstance(str_like, str)
    assert type(str_like) is not str
    resolved = _resolve(BASE_DIR, str_like, setting)
    assert len(resolved) == 0


def test_extension_filter() -> None:
    python_file = pathlib.Path("python.py")
    cython_file = pathlib.Path("cython.pyx")
    stub_file = pathlib.Path("stub.pyi")
    markdown_file = pathlib.Path("markdown.md")
    text_file = pathlib.Path("text.txt")
    c_file = pathlib.Path("source.c")
    cpp_file = pathlib.Path("source.cpp")
    header_file = pathlib.Path("header.h")

    source = [
        python_file,
        cython_file,
        stub_file,
        markdown_file,
        text_file,
        c_file,
        cpp_file,
        header_file,
    ]

    assert [x for x in source if PythonFileFilter(x)] == [python_file, stub_file]

    predicate = extension_filter({".cpp", ".c", ".h"})
    assert [x for x in source if predicate(x)] == [c_file, cpp_file, header_file]


def test_add_remove() -> None:
    source = Source(includes=["hoge", "fuga"], excludes=["piyo"])

    with pytest.raises(KeyError):
        source.remove_include("foo")
    with pytest.raises(KeyError):
        source.remove_exclude("bar")

    source.add_include("foo")
    source.add_include("foo")
    source.remove_include("foo")
    with pytest.raises(KeyError):
        source.remove_include("foo")

    source.add_exclude("bar")
    source.add_exclude("bar")
    source.remove_exclude("bar")
    with pytest.raises(KeyError):
        source.remove_exclude("bar")

    source.remove_include("hoge")
    source.remove_include("fuga")
    source.remove_exclude("piyo")


def touch_file(path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


@contextlib.contextmanager
def create_git_repository(
    tracked_files: Set[str], untracked_files: Set[str]
) -> Iterator[pathlib.Path]:
    files = tracked_files.union(untracked_files)
    assert len(files) == len(tracked_files) + len(
        untracked_files
    )  # assert intersection is empty

    with tempfile.TemporaryDirectory() as d:
        base_dir = pathlib.Path(d)
        with change_dir(base_dir):
            repo = git.Repo.init()
            for f in files:
                touch_file(pathlib.Path(f))

            repo.index.add(list(tracked_files))
            yield base_dir


def test_resolve_files_root_dot() -> None:
    tracked_files = {
        "A/0.md",
        "A/1.py",
        "A/stubs/0.pyi",
        "A/stubs/1.md",
        "A/stubs/2.md",
        "0.py",
        "1.md",
    }
    untracked_files = {
        "A/2.md",
        "A/3.py",
        "A/stubs/3.pyi",
        "A/stubs/4.md",
        "A/stubs/5.md",
        "2.py",
        "3.md",
    }

    source = Source()
    source.add_include(".")

    with create_git_repository(tracked_files, untracked_files) as base_dir:
        expected_tracked = {
            base_dir / "A/1.py",
            base_dir / "A/stubs/0.pyi",
            base_dir / "0.py",
        }
        expected_untracked = {
            base_dir / "A/3.py",
            base_dir / "A/stubs/3.pyi",
            base_dir / "2.py",
        }
        assert (
            source.resolve_files(base_dir, PythonFileFilter, use_git=True)
            == expected_tracked
        )
        assert source.resolve_files(
            base_dir, PythonFileFilter, use_git=False
        ) == expected_tracked.union(expected_untracked)


def test_resolve_files_include_file() -> None:
    tracked_files = {
        "A/0.md",
        "A/1.py",
        "0.py",
        "1.md",
    }
    untracked_files = {
        "A/2.md",
        "A/3.py",
        "2.py",
        "3.md",
    }

    source = Source()
    source.add_include("A")

    with create_git_repository(tracked_files, untracked_files) as base_dir:
        expected_tracked = {
            base_dir / "A/1.py",
        }
        expected_untracked = {
            base_dir / "A/3.py",
        }
        assert (
            source.resolve_files(base_dir, PythonFileFilter, use_git=True)
            == expected_tracked
        )
        assert source.resolve_files(
            base_dir, PythonFileFilter, use_git=False
        ) == expected_tracked.union(expected_untracked)

        source.add_include("1.md")
        source.add_include("3.md")

        expected_tracked.add(base_dir / "1.md")
        expected_untracked.add(base_dir / "3.md")

        assert (
            source.resolve_files(base_dir, PythonFileFilter, use_git=True)
            == expected_tracked
        )
        assert source.resolve_files(
            base_dir, PythonFileFilter, use_git=False
        ) == expected_tracked.union(expected_untracked)

        source.add_include("**/*.md", glob=True)

        expected_tracked.add(base_dir / "A/0.md")
        expected_untracked.add(base_dir / "A/2.md")

        assert (
            source.resolve_files(base_dir, PythonFileFilter, use_git=True)
            == expected_tracked
        )
        assert source.resolve_files(
            base_dir, PythonFileFilter, use_git=False
        ) == expected_tracked.union(expected_untracked)


def test_resolve_files_exclude() -> None:
    tracked_files = {
        "A/1.py",
        "A/third_party/1.py",
        "A/third_party/nested/1.py",
        "A/third_party/2.md",
        "0.py",
        "1.md",
    }
    untracked_files = {
        "A/2.py",
        "A/third_party/3.py",
        "A/third_party/nested/2.py",
        "A/third_party/4.md",
        "2.py",
        "3.md",
    }

    source = Source()
    source.add_include(".")

    with create_git_repository(tracked_files, untracked_files) as base_dir:
        expected_tracked = {
            base_dir / "A/1.py",
            base_dir / "A/third_party/1.py",
            base_dir / "A/third_party/nested/1.py",
            base_dir / "0.py",
        }
        expected_untracked = {
            base_dir / "A/2.py",
            base_dir / "A/third_party/3.py",
            base_dir / "A/third_party/nested/2.py",
            base_dir / "2.py",
        }
        assert (
            source.resolve_files(base_dir, PythonFileFilter, use_git=True)
            == expected_tracked
        )
        assert source.resolve_files(
            base_dir, PythonFileFilter, use_git=False
        ) == expected_tracked.union(expected_untracked)

        source.add_exclude("0.py")
        source.add_exclude("2.py")

        expected_tracked.remove(base_dir / "0.py")
        expected_untracked.remove(base_dir / "2.py")

        assert (
            source.resolve_files(base_dir, PythonFileFilter, use_git=True)
            == expected_tracked
        )
        assert source.resolve_files(
            base_dir, PythonFileFilter, use_git=False
        ) == expected_tracked.union(expected_untracked)

        source.add_exclude("A/third_party/**/*.py", glob=True)

        expected_tracked = {
            base_dir / "A/1.py",
        }
        expected_untracked = {
            base_dir / "A/2.py",
        }
        assert (
            source.resolve_files(base_dir, PythonFileFilter, use_git=True)
            == expected_tracked
        )
        assert source.resolve_files(
            base_dir, PythonFileFilter, use_git=False
        ) == expected_tracked.union(expected_untracked)


def test_copy() -> None:
    source = Source()
    source.add_include("hoge", glob=True, base_dir=pathlib.Path("/hoge"))
    source.add_include("fuga", glob=False)
    source.add_exclude("piyo", glob=True, base_dir=pathlib.Path("/fuga"))

    copied = source.copy()

    assert source.includes == copied.includes
    assert source.includes is not copied.includes
    assert source.excludes == copied.excludes
    assert source.excludes is not copied.excludes

    source.add_include("foo", glob=True)
    copied.add_exclude("bar", glob=False)

    assert source.includes.keys() == {"hoge", "fuga", "foo"}
    assert copied.includes.keys() == {"hoge", "fuga"}
    assert copied.includes == {
        "hoge": SourceEntrySetting(glob=True, base_dir=pathlib.Path("/hoge")),
        "fuga": SourceEntrySetting(glob=False),
    }

    assert source.excludes.keys() == {"piyo"}
    assert copied.excludes.keys() == {"piyo", "bar"}
    assert copied.excludes == {
        "piyo": SourceEntrySetting(glob=True, base_dir=pathlib.Path("/fuga")),
        "bar": SourceEntrySetting(glob=False),
    }
