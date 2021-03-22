import logging
import pathlib
from typing import Any, List, Optional, Sequence

import pysen.pyproject  # NOQA

from ._version import __version__  # NOQA
from .black import Black, BlackSetting  # NOQA
from .command import CommandBase  # NOQA
from .component import ComponentBase  # NOQA
from .factory import ConfigureLintOptions, configure_lint  # NOQA
from .flake8 import Flake8, Flake8Setting  # NOQA
from .isort import Isort, IsortSetting  # NOQA
from .lint_command import SingleFileFormatCommandBase, SingleFileLintCommandBase  # NOQA
from .logging_utils import setup_logger  # NOQA
from .manifest import Manifest, ManifestBase  # NOQA
from .manifest_builder import build as build_manifest  # NOQA
from .mypy import Mypy, MypyPreset, MypySetting, MypyTarget  # NOQA
from .path import PathLikeType  # NOQA
from .plugin import PluginBase, PluginConfig  # NOQA
from .py_version import PythonVersion  # NOQA
from .pyproject import load_manifest  # NOQA
from .pyproject_model import Config  # NOQA
from .reporter import ReporterFactory  # NOQA
from .runner import Runner  # NOQA
from .runner_options import RunOptions  # NOQA
from .source import Source  # NOQA

_logger = logging.getLogger(__name__)


try:
    from .setuptools import generate_setting_files  # NOQA isort:skip
    from .setuptools import setup  # NOQA isort:skip
    from .setuptools import setup_from_pyproject  # NOQA isort:skip
except ImportError:
    _logger.warning("[pysen.setuptools] failed to import setuptools")


def run(
    base_dir: pathlib.Path,
    target_name: str,
    manifest_args: Optional[Sequence[str]] = None,
    reporter_factory: Optional[ReporterFactory] = None,
    *,
    settings_dir: Optional[pathlib.Path] = None,
    options: Optional[RunOptions] = None,
    pyproject: Optional[pathlib.Path] = None,
    components: Optional[Sequence[ComponentBase]] = None,
    manifest: Optional[ManifestBase] = None,
) -> bool:
    func_args: List[Any] = [x is not None for x in (pyproject, components, manifest)]
    if func_args.count(True) != 1:
        raise ValueError(
            "only one of pyproject, components, and manifest must be specified"
        )

    target: ManifestBase
    if manifest is not None:
        target = manifest
    elif components is not None:
        target = build_manifest(list(components))
    else:
        assert pyproject is not None
        target = load_manifest(pyproject)

    manifest_args = manifest_args or []
    reporter_factory = reporter_factory or ReporterFactory()

    assert manifest_args is not None
    assert reporter_factory is not None

    runner = Runner(target)
    parsed_args = runner.parse_manifest_arguments(manifest_args)
    options = options or RunOptions()
    runner.run(
        target_name,
        base_dir,
        parsed_args,
        reporter_factory,
        options,
        files=None,
        settings_dir=settings_dir,
    )

    return not reporter_factory.has_error()
