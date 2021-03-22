import dataclasses
import pathlib
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set

from .git_utils import GitRepositoryNotFoundError, check_tracked, list_indexed_files
from .path import PathLikeType, is_contained, resolve_path
from .reporter import Reporter

FilePredicateType = Callable[[pathlib.Path], bool]


def extension_filter(accept_extensions: Set[str]) -> FilePredicateType:
    def impl(path: pathlib.Path) -> bool:
        return path.suffix in accept_extensions

    return impl


PythonFileFilter = extension_filter({".py", ".pyi"})


@dataclasses.dataclass
class SourceEntrySetting:
    glob: bool
    base_dir: Optional[pathlib.Path] = None


def _resolve(
    base_dir: pathlib.Path, p: PathLikeType, setting: SourceEntrySetting
) -> List[pathlib.Path]:
    if isinstance(p, pathlib.Path) and setting.glob:
        raise RuntimeError("cannot use pathlib.Path when glob=True")

    if setting.base_dir is not None:
        base_dir = setting.base_dir
    base_dir = base_dir.resolve()

    if not setting.glob:
        return [resolve_path(base_dir, p)]

    assert isinstance(p, str)
    # NOTE(igarashi): ensure that p is an instance of str
    # otherwise, pathlib.glob raises an error when sys.intern() is called
    p = str(p)

    # NOTE(igarashi): pathlib.Path.glob(".") raises IndexError in Python 3.7 (might be a bug?)
    # To avoid the bug, add a condition to handle the case for the workaround.
    if p == ".":
        return [resolve_path(base_dir, ".")]

    # run base_dir.glob only if isinstance(p, str) and setting.glob
    return [resolve_path(base_dir, g) for g in base_dir.glob(p)]


class Source:
    def __init__(
        self,
        includes: Optional[Sequence[PathLikeType]] = None,
        excludes: Optional[Sequence[PathLikeType]] = None,
        include_globs: Optional[Sequence[PathLikeType]] = None,
        exclude_globs: Optional[Sequence[PathLikeType]] = None,
    ) -> None:
        self._includes: Dict[PathLikeType, SourceEntrySetting] = {}
        self._excludes: Dict[PathLikeType, SourceEntrySetting] = {}

        if includes is not None:
            for i in includes:
                self.add_include(i, glob=False)

        if include_globs is not None:
            for i in include_globs:
                self.add_include(i, glob=True)

        if excludes is not None:
            for e in excludes:
                self.add_exclude(e, glob=False)

        if exclude_globs is not None:
            for e in exclude_globs:
                self.add_exclude(e, glob=True)

    def add_include(
        self,
        entry: PathLikeType,
        *,
        glob: bool = False,
        base_dir: Optional[pathlib.Path] = None,
    ) -> None:
        self._includes[entry] = SourceEntrySetting(glob=glob, base_dir=base_dir)

    def add_exclude(
        self,
        entry: PathLikeType,
        *,
        glob: bool = False,
        base_dir: Optional[pathlib.Path] = None,
    ) -> None:
        self._excludes[entry] = SourceEntrySetting(glob=glob, base_dir=base_dir)

    def remove_include(self, entry: PathLikeType) -> None:
        self._includes.pop(entry)

    def remove_exclude(self, entry: PathLikeType) -> None:
        self._excludes.pop(entry)

    @property
    def includes(self) -> Dict[PathLikeType, SourceEntrySetting]:
        return self._includes

    @property
    def excludes(self) -> Dict[PathLikeType, SourceEntrySetting]:
        return self._excludes

    def copy(self) -> "Source":
        new = Source()
        for path, setting in self.includes.items():
            new.add_include(path, glob=setting.glob, base_dir=setting.base_dir)

        for path, setting in self.excludes.items():
            new.add_exclude(path, glob=setting.glob, base_dir=setting.base_dir)

        return new

    def iter_include_entries(self, base_dir: pathlib.Path) -> Iterable[pathlib.Path]:
        for include, setting in self._includes.items():
            yield from iter(_resolve(base_dir, include, setting))

    def iter_exclude_entries(self, base_dir: pathlib.Path) -> Iterable[pathlib.Path]:
        for exclude, setting in self._excludes.items():
            yield from iter(_resolve(base_dir, exclude, setting))

    def _resolve_include_files(
        self,
        base_dir: pathlib.Path,
        filter_predicate: FilePredicateType,
        use_git: bool,
        reporter: Optional[Reporter] = None,
    ) -> Set[pathlib.Path]:
        includes = self.iter_include_entries(base_dir)

        included_files: Set[pathlib.Path] = set()

        for include in includes:
            if not include.exists():
                continue
            if include.is_file():
                # NOTE(igarashi): include this file anyway even though it is
                # not a .py file (e.g., script/command)
                if use_git:
                    try:
                        if not check_tracked(include):
                            continue
                    except GitRepositoryNotFoundError:
                        if reporter is not None:
                            reporter.logger.warning(
                                f"{include} is outside repository. ignored."
                            )

                included_files.add(include)
            else:
                if use_git:
                    try:
                        included_files.update(
                            x
                            for x in list_indexed_files(include)
                            if filter_predicate(x)
                        )
                    except GitRepositoryNotFoundError:
                        if reporter is not None:
                            reporter.logger.warning(
                                f"{include} is outside repository. ignored."
                            )
                else:
                    included_files.update(
                        x for x in include.glob("**/*") if filter_predicate(x)
                    )

        return included_files

    def resolve_files(
        self,
        base_dir: pathlib.Path,
        filter_predicate: Optional[FilePredicateType],
        use_git: bool = True,
        reporter: Optional[Reporter] = None,
    ) -> Set[pathlib.Path]:
        """Returns a set of target files.
        Note:
            `filter_predicate` is used to filter files only when a directory is expanded by
            the system. If an user explicitly specifies the path as included, it will be added
            to the return object.

        Examples:
            >>> s = Source(includes=["foo/", "bar/doc.md"])
            >>> s.resolve_files(base_dir, lambda x: x.suffix == ".py")
            [PosixPath("foo/main.py"), PosixPath("foo/module.py"), PosixPath("bar/doc.md")]
        """

        def _default(x: pathlib.Path) -> bool:
            return True

        filter_predicate = filter_predicate or _default

        assert base_dir.is_absolute()

        included = self._resolve_include_files(
            base_dir, filter_predicate, use_git, reporter
        )

        exclude_entries = list(self.iter_exclude_entries(base_dir))

        def exclude_filter(path: pathlib.Path) -> bool:
            return not any(is_contained(exclude, path) for exclude in exclude_entries)

        return set(filter(exclude_filter, included))
