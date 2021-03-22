import dataclasses
import re
from typing import Optional


def _coerce_type(s: Optional[str]) -> Optional[int]:
    if s is None:
        return None
    else:
        return int(s)


@dataclasses.dataclass(frozen=True)
class VersionRepresentation:
    major: int
    minor: int
    patch: Optional[int] = None
    pre_release: Optional[str] = None

    @property
    def version(self) -> str:
        s = f"{self.major}.{self.minor}"
        if self.patch is not None:
            s += f".{self.patch}"

        return s

    @classmethod
    def from_str(cls, s: str) -> "VersionRepresentation":
        number = r"(?:0|[1-9]\d*)"
        major = fr"^(?P<major>{number})"
        minor = fr"\.(?P<minor>{number})"
        patch = fr"(\.(?P<patch>{number}))?"
        pre_release = fr"(?P<pre_release>(a|b|rc){number})?$"
        pattern = major + minor + patch + pre_release
        m = re.match(pattern, s)

        if m is not None:
            return cls(
                major=int(m.group("major")),
                minor=int(m.group("minor")),
                patch=_coerce_type(m.group("patch")),
                pre_release=m.group("pre_release"),
            )
        raise ValueError("Invalid version format. See PEP 440 for details.")

    def __str__(self) -> str:
        major = self.major
        minor = self.minor
        if self.patch is None:
            patch = ""
        else:
            # notice the preceding dot (.)
            patch = f".{self.patch}"
        pre_release = self.pre_release or ""
        return f"{major}.{minor}{patch}{pre_release}"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, VersionRepresentation):
            # we might compare None and [int, str]
            return all(
                (
                    self.major == other.major,
                    self.minor == other.minor,
                    self.patch == other.patch,
                    self.pre_release == other.pre_release,
                )
            )
        else:
            raise NotImplementedError

    def is_compatible(self, other: "VersionRepresentation") -> bool:
        return self.major == other.major and self.minor == other.minor


@dataclasses.dataclass(frozen=True)
class PythonVersion(VersionRepresentation):
    @property
    def full_representation(self) -> str:
        return f"Python{self.version}"

    @property
    def short_representation(self) -> str:
        return f"py{self.major}{self.minor}"

    @staticmethod
    def parse_short_representation(value: str) -> "PythonVersion":
        try:
            return _PythonVersions[value.upper()]
        except KeyError:
            raise KeyError(
                f"invalid value: {value}, must be one of {_PythonVersions.keys()}"
            ) from None


# NOTE(igarashi): PythonVersion class is immutable
_PythonVersions = {
    "PY27": PythonVersion(2, 7),
    "PY36": PythonVersion(3, 6),
    "PY37": PythonVersion(3, 7),
    "PY38": PythonVersion(3, 8),
    "PY39": PythonVersion(3, 9),
}
