import pathlib


class PysenError(Exception):
    pass


class CommandNotFoundError(PysenError):
    pass


class PysenSectionNotFoundError(PysenError):
    pass


class InvalidCommandNameError(PysenError):
    def __init__(self, name: str) -> None:
        super().__init__(f"invalid command name: {name}")


class InvalidConfigurationError(PysenError):
    pass


class InvalidPluginError(PysenError):
    def __init__(self, module_path: str, error: str) -> None:
        super().__init__(f"invalid plugin: {module_path}, {error}")


class InvalidManifestBuilderError(PysenError):
    def __init__(self, path: pathlib.Path, error: str) -> None:
        super().__init__(f"invalid manifest builder: {path}, {error}")


class UnexpectedErrorFormat(PysenError):
    pass


class IncompatibleVersionError(PysenError):
    pass


class DistributionNotFound(PysenError):
    pass


class InvalidComponentName(PysenError):
    pass


class RunTargetFileNotSupported(PysenError):
    pass
