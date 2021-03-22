import pathlib
from unittest import mock

import setuptools
import setuptools.command.build_py

from pysen.setuptools import (
    _PREDEFINED_COMMAND_NAMES,
    _create_setuptool_command,
    _get_setuptool_command,
    _get_setuptool_user_options,
)

FAKE_PATH = pathlib.Path(__file__).resolve().parent


def test__get_setuptool_command() -> None:
    build_py = _get_setuptool_command("build_py")
    assert build_py is setuptools.command.build_py.build_py

    abstract_init_opt = setuptools.Command.initialize_options
    abstract_final_opt = setuptools.Command.finalize_options
    abstract_run = setuptools.Command.run

    for name in _PREDEFINED_COMMAND_NAMES:
        cmd = _get_setuptool_command(name)
        assert cmd is not None
        assert issubclass(cmd, setuptools.Command)
        assert cmd is not setuptools.Command

        # NOTE(igarashi): assert that all the predefined methods don't have any references to
        # the abstract method of setuptools.Command.
        assert cmd.initialize_options is not abstract_init_opt
        assert cmd.finalize_options is not abstract_final_opt
        assert cmd.run is not abstract_run

    cmd = _get_setuptool_command("foo")
    assert cmd is not None
    assert issubclass(cmd, setuptools.Command)
    assert cmd is setuptools.Command


def test__get_setuptool_user_options() -> None:
    build_py_options = _get_setuptool_user_options(setuptools.command.build_py.build_py)
    assert build_py_options is not None
    assert len(build_py_options) > 0

    command_options = _get_setuptool_user_options(setuptools.Command)
    assert command_options is not None
    assert command_options == []


def test__create_setuptool_command_inheritance() -> None:
    build_py = _create_setuptool_command(
        "build_py", mock.Mock(), FAKE_PATH, None, mock.Mock()
    )
    assert build_py is not None
    assert issubclass(build_py, setuptools.command.build_py.build_py)
    assert build_py is not setuptools.command.build_py.build_py

    foo = _create_setuptool_command("foo", mock.Mock(), FAKE_PATH, None, mock.Mock())
    assert foo is not None
    assert not issubclass(foo, setuptools.command.build_py.build_py)
    assert issubclass(foo, setuptools.Command)
