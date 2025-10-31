import dataclasses
import pathlib
from collections import OrderedDict
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)

from .types import MAPPING_TYPES, PRIMITIVE_TYPES, SEQUENCE_TYPES

TypeHookCallback = Callable[[Any], Any]


def to_dash_case(s: str) -> str:
    # convert field name to dash-case
    # Example: snake_case to snake-case
    return s.replace("_", "-")


@dataclasses.dataclass
class SettingBase:
    def asdict(
        self,
        ignore_fields: Optional[Sequence[str]] = None,
        omit_none: bool = False,
        naming_rule: Optional[Callable[[str], str]] = None,
        renames: Optional[Dict[str, str]] = None,
        type_hooks: Optional[Dict[Type[Any], TypeHookCallback]] = None,
    ) -> Dict[str, Any]:
        entries = dataclasses.asdict(self)
        if ignore_fields is not None:
            for ignore in ignore_fields:
                assert ignore in entries
                entries.pop(ignore)

        if omit_none:
            empty = [k for k, v in entries.items() if v is None]
            for k in empty:
                entries.pop(k)

        if renames is not None:
            for src, to in renames.items():
                if src in entries:
                    value = entries.pop(src)
                    entries[to] = value

        field_name_converter: Callable[[str], str] = lambda s: s
        if naming_rule is not None:
            field_name_converter = naming_rule

        type_conversion: Dict[Type[Any], TypeHookCallback] = {
            pathlib.Path: lambda x: str(x),
        }
        if type_hooks is not None:
            type_conversion.update(type_hooks)

        def convert_types(data: Any) -> Any:
            if data is None:
                return None

            data_type = type(data)
            conversion = type_conversion.get(data_type, None)
            if conversion is not None:
                return conversion(data)

            if isinstance(data, PRIMITIVE_TYPES):
                return data
            elif isinstance(data, SEQUENCE_TYPES):
                return list(sorted([convert_types(x) for x in data]))
            elif isinstance(data, MAPPING_TYPES):
                # NOTE(igarashi): key must be a str
                return OrderedDict(
                    (field_name_converter(k), convert_types(v))
                    for k, v in sorted(data.items())
                )
            else:
                raise RuntimeError(
                    f"cannot handle type: {data_type}, consider adding type_hooks"
                )

        return cast(Dict[str, Any], convert_types(entries))


SectionPathType = Sequence[str]
SectionDataType = Dict[str, Any]


def _sort_object(data: Any) -> Any:
    if data is None:
        return None

    if isinstance(data, PRIMITIVE_TYPES):
        return data
    elif isinstance(data, SEQUENCE_TYPES):
        return list(sorted(data))
    elif isinstance(data, MAPPING_TYPES):
        return OrderedDict((k, _sort_object(v)) for k, v in sorted(data.items()))
    else:
        raise RuntimeError(f"cannot handle type: {type(data)}")


def _create_dict(paths: SectionPathType) -> Any:
    element: Dict[str, Any] = {}
    for path in paths[::-1]:
        element = {path: element}
    return element


def _traverse_toml(
    section_path: SectionPathType, toml: Dict[str, Any], create: bool
) -> Any:
    element = toml
    current_path: List[str] = []
    for idx, path in enumerate(section_path):
        if path in element:
            element = element[path]
        elif create:
            # create remaining items and set create=False so that we don't create nodes anymore
            element[path] = _create_dict(section_path[idx + 1 :])
            create = False

            # re-create the reference from toml root
            element = _traverse_toml(section_path[: idx + 1], toml, False)
        else:
            raise ValueError(f"Key {path} does not exist")

        current_path.append(path)
        if not isinstance(element, dict):
            raise KeyError(f"invalid section, {current_path} exists")

    return element


class SettingFile:
    def __init__(self) -> None:
        self._entries: List[Tuple[SectionPathType, SectionDataType]] = []
        self._structure: Set[Tuple[str, ...]] = set()

    def entries(self) -> List[Tuple[SectionPathType, Dict[str, Any]]]:
        return self._entries

    @staticmethod
    def update_by_entry(
        dst: Dict[str, Any],
        section_path: SectionPathType,
        section_data: SectionDataType,
        replace: bool = True,
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = _traverse_toml(section_path, dst, True)
        parent = _traverse_toml(section_path[:-1], dst, False)

        if replace:
            # NOTE(igarashi): tomlkit.TOMLDocument doesn't clear its dictionary by `clear()`,
            # so we set a new dict from its parent
            parent[section_path[-1]] = {}
            data = _traverse_toml(section_path, dst, False)

        # NOTE(igarashi): don't use dict.update so that the items are added
        # in alphabetical order.
        for key, value in sorted(section_data.items()):
            data[key] = _sort_object(value)

        return data

    def as_dict(self) -> Dict[str, Any]:
        root: Dict[str, Any] = {}
        for entry in self._entries:
            SettingFile.update_by_entry(root, entry[0], entry[1])

        return root

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, dict):
            return other == self.as_dict()

        return id(other) == id(self)

    def get_section(
        self,
        path: Union[str, SectionPathType],
        default: Optional[SectionDataType] = None,
    ) -> SectionDataType:
        target: Tuple[str, ...]
        if isinstance(path, str):
            target = (path,)
        else:
            target = tuple(path)

        for p, d in self._entries:
            if p == target:
                return d

        if default is not None:
            return default

        raise KeyError(f"section: {path} not found")

    def set_section(self, path: SectionPathType, data: SectionDataType) -> None:
        assert isinstance(path, (tuple, list))
        subpath: List[str] = []
        for p in path:
            if tuple(subpath) in self._structure:
                raise KeyError(f"subpath: {subpath} already exists")

            subpath.append(p)

        self._entries.append((tuple(path), data))
