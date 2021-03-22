from pysen._version import __version__
from pysen.py_version import VersionRepresentation


def test__version() -> None:
    # version string MUST be in a format the VersionRepresentation understands
    VersionRepresentation.from_str(__version__)
