import pathlib
import tempfile
from typing import Sequence

import git
import pytest
from _pytest.monkeypatch import MonkeyPatch

from pysen import git_utils
from pysen.git_utils import GitRepositoryNotFoundError

BASE_DIR = pathlib.Path(__file__).resolve().parent


def test_check_git_available() -> None:
    with tempfile.TemporaryDirectory() as d:
        tempdir = pathlib.Path(d)
        assert git_utils._check_git_enabled()
        assert not git_utils.check_git_available(tempdir)

        git.Repo.init(tempdir)
        assert git_utils._check_git_enabled()
        assert git_utils.check_git_available(tempdir)


def test_skip_git_check(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("PYSEN_IGNORE_GIT", "1")
    with tempfile.TemporaryDirectory() as d:
        tempdir = pathlib.Path(d)
        assert not git_utils._check_git_enabled()
        assert not git_utils.check_git_available(tempdir)

        git.Repo.init(tempdir)
        assert not git_utils._check_git_enabled()
        assert not git_utils.check_git_available(tempdir)


def test_dont_skip_git_check(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("PYSEN_IGNORE_GIT", "0")
    with tempfile.TemporaryDirectory() as d:
        tempdir = pathlib.Path(d)
        assert not git_utils.check_git_available(tempdir)

        git.Repo.init(tempdir)
        assert git_utils.check_git_available(tempdir)


def test_list_indexed_files() -> None:
    def list_indexed_files(target_dir: pathlib.Path) -> Sequence[pathlib.Path]:
        ret = git_utils.list_indexed_files(target_dir)
        git_utils.list_indexed_files.cache_clear()
        return ret

    with tempfile.TemporaryDirectory() as d:
        tempdir = pathlib.Path(d).resolve()

        with pytest.raises(GitRepositoryNotFoundError):
            list(list_indexed_files(tempdir))

        repo = git.Repo.init(tempdir)

        assert list(list_indexed_files(tempdir)) == []

        test_file = tempdir / "hoge"
        test_file.touch()

        assert list(list_indexed_files(tempdir)) == []
        repo.index.add([str(test_file)])

        assert list(list_indexed_files(tempdir)) == [test_file]

        test_dir = tempdir / "foo"
        test_dir2 = tempdir / "foo_2"

        test_dir.mkdir()
        test_dir2.mkdir()

        test_file2 = test_dir / "a"
        test_file2.touch()

        test_file3 = test_dir2 / "b"
        test_file3.touch()

        repo.index.add([str(test_file2), str(test_file3)])
        assert set(list_indexed_files(tempdir)) == {
            test_file,
            test_file2,
            test_file3,
        }
        assert set(list_indexed_files(tempdir / "foo")) == {test_file2}
        assert set(list_indexed_files(tempdir / "foo_2")) == {test_file3}

        assert set(list_indexed_files(tempdir)) == {test_file, test_file2, test_file3}
        # a file is removed without being staged
        test_file3.unlink()
        assert set(list_indexed_files(tempdir)) == {test_file, test_file2}


def test_check_tracked() -> None:
    with tempfile.TemporaryDirectory() as d:
        tempdir = pathlib.Path(d)

        test_file = tempdir / "hoge"
        test_file.touch()

        with pytest.raises(GitRepositoryNotFoundError):
            git_utils.check_tracked(test_file)

        repo = git.Repo.init(tempdir)
        assert not git_utils.check_tracked(test_file)

        repo.index.add([str(test_file)])

        assert git_utils.check_tracked(test_file)
