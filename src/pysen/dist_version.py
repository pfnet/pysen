import logging
from importlib.metadata import Distribution, PackageNotFoundError, distribution
from typing import Optional

from pysen.exceptions import DistributionNotFound
from pysen.py_version import VersionRepresentation

_logger = logging.getLogger(__name__)


def _get_distro(name: str) -> Optional[Distribution]:
    try:
        return distribution(name)
    except PackageNotFoundError:
        _logger.debug(f"distribution {name} not found", exc_info=True)
        return None


def get_version(name: str) -> VersionRepresentation:
    distro = _get_distro(name)
    if distro is None:
        raise DistributionNotFound(
            f"Expected {name} to be installed but importlib could not find it.\n"
            f'Hint: Did you install "{name}" in the same Python environment as pysen?'
        )
    return VersionRepresentation.from_str(distro.version)
