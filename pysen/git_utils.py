import functools
import logging
import os
import pathlib
import threading
from typing import Sequence, Tuple, cast

_logger = logging.getLogger(__name__)
_lock = threading.Lock()

try:
    import git

    _git_available = True
except ImportError:
    _git_available = False
    _logger.warning("[pysen.git_utils] git is not available")


class GitRepositoryNotFoundError(Exception):
    pass


def _check_git_enabled() -> bool:
    if not _git_available:
        return False

    if os.environ.get("PYSEN_IGNORE_GIT", "0") != "0":
        return False

    return True


def check_git_available(target_dir: pathlib.Path) -> bool:
    with _lock:
        try:
            if not _check_git_enabled():
                return False

            with git.Repo(target_dir, search_parent_directories=True):
                return True
        except git.InvalidGitRepositoryError:
            return False


def _list_indexed_files(target_dir: pathlib.Path) -> Sequence[pathlib.Path]:
    if not _check_git_enabled():
        return []

    # Ensure abs_target_dir ends with /
    # We avoid pathlib.Path because the loop calling predicate is performance critical.
    abs_target_dir = os.path.join(str(target_dir.resolve()), "")

    def predicate(item: Tuple[int, git.Blob]) -> bool:
        blob = item[1]
        ret: bool = blob.abspath.startswith(abs_target_dir)
        return ret

    try:
        with git.Repo(target_dir, search_parent_directories=True) as repo:
            deleted_files = set(
                diff.a_blob.abspath
                for diff in repo.index.diff(None)
                if diff.change_type == "D"
            )
            blobs = set(blob.abspath for _, blob in repo.index.iter_blobs(predicate))
            return [pathlib.Path(abspath) for abspath in blobs - deleted_files]
    except git.InvalidGitRepositoryError:
        raise GitRepositoryNotFoundError() from None


@functools.lru_cache(8)
def list_indexed_files(target_dir: pathlib.Path) -> Sequence[pathlib.Path]:
    with _lock:
        return _list_indexed_files(target_dir)


def _check_tracked(path: pathlib.Path) -> bool:
    if not _check_git_enabled():
        return False

    # TODO(igarashi) use git command directly for better performance
    abspath = str(path.expanduser().resolve())

    def predicate(item: Tuple[int, git.Blob]) -> bool:
        blob = item[1]
        return cast(bool, blob.abspath == abspath)

    try:
        with git.Repo(path, search_parent_directories=True) as repo:
            items = list(repo.index.iter_blobs(predicate))
            return len(items) > 0
    except git.InvalidGitRepositoryError:
        raise GitRepositoryNotFoundError() from None


def check_tracked(path: pathlib.Path) -> bool:
    with _lock:
        return _check_tracked(path)
