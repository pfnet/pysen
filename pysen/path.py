import contextlib
import os
import pathlib
from typing import Iterable, Iterator, Union

PathLikeType = Union[pathlib.Path, str]


def wrap_path(s: PathLikeType) -> pathlib.Path:
    if isinstance(s, pathlib.Path):
        return s
    return pathlib.Path(s)


def resolve_path(base_dir: pathlib.Path, path: PathLikeType) -> pathlib.Path:
    return (base_dir / path).expanduser().resolve()


def get_relative_path(path: PathLikeType, base_dir: pathlib.Path) -> str:
    pth = wrap_path(path)
    if not pth.is_absolute():
        return str(pth)

    return os.path.relpath(pth, base_dir)


@contextlib.contextmanager
def change_dir(dst: pathlib.Path) -> Iterator[None]:
    old = pathlib.Path.cwd()
    try:
        os.chdir(dst)
        yield
    finally:
        os.chdir(old)


def is_covered(path: pathlib.Path, sources: Iterable[pathlib.Path]) -> bool:
    """
    Checks if `path` is contained in any of the subdirectories in sources.
    See the test cases for details.
    """
    path = path.resolve()
    abs_path = [source.resolve() for source in sources]
    return any(c in abs_path for c in list(path.parents) + [path])


def is_contained(parent: pathlib.Path, child: pathlib.Path) -> bool:
    if not parent.is_absolute() or not child.is_absolute():
        raise ValueError("Argument 'parent' and 'child' must be absolute")
    return str(child).startswith(str(parent))
