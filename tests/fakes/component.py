import enum
import pathlib
from typing import DefaultDict, Dict, List, Optional, Sequence, Tuple

from pysen import ComponentBase
from pysen.command import CommandBase
from pysen.diagnostic import Diagnostic
from pysen.reporter import Reporter
from pysen.runner_options import PathContext, RunOptions
from pysen.setting import SettingFile


class Operation(enum.Enum):
    ADD = "+"
    MUL = "*"


class FakeCommand(CommandBase):
    def __init__(
        self, coef: int, op: Operation, ref: List[float], options: RunOptions
    ) -> None:
        self.coef = coef
        self.op = op
        self.ref = ref
        self.options = options
        assert len(ref) == 1

    @property
    def name(self) -> str:
        return f"{self.op.value} {self.coef}"

    def __call__(self, reporter: Reporter) -> int:
        value = self.ref[0]
        coef = float(self.coef)

        if self.op == Operation.ADD:
            value += coef
        elif self.op == Operation.MUL:
            value *= coef
        else:
            raise AssertionError(f"invalid op: {self.op}")

        self.ref[0] = value

        if value >= 0.0:
            return 0
        else:
            if self.options.require_diagnostics:
                reporter.report_diagnostics(
                    [Diagnostic(pathlib.Path(".").resolve(), message="")]
                )
            return 1


class FakeComponent(ComponentBase):
    def __init__(
        self,
        name: str,
        ops: Dict[str, Tuple[int, Operation]],
        expected_base_dir: Optional[pathlib.Path],
        expected_settings_dir: Optional[pathlib.Path],
        ref: List[float],
    ) -> None:
        self._name = name
        self._ops = ops
        self._expected_base_dir = expected_base_dir
        self._expected_settings_dir = expected_settings_dir
        self._ref = ref
        assert len(ref) == 1

    @property
    def name(self) -> str:
        return self._name

    def export_settings(
        self,
        paths: PathContext,
        files: DefaultDict[str, SettingFile],
    ) -> None:
        if self._expected_base_dir is not None:
            assert paths.base_dir == self._expected_base_dir
        if self._expected_settings_dir is not None:
            assert paths.settings_dir == self._expected_settings_dir
        for name, op in self._ops.items():
            fname = f"{name}.yaml"
            setting_file = files[fname]
            setting_file.set_section((self.name,), {"coef": op[0], "op": op[1].value})

    @property
    def targets(self) -> Sequence[str]:
        return list(self._ops.keys())

    def create_command(
        self, target: str, paths: PathContext, options: RunOptions
    ) -> CommandBase:
        if self._expected_base_dir is not None:
            assert paths.base_dir == self._expected_base_dir
        if self._expected_settings_dir is not None:
            assert paths.settings_dir == self._expected_settings_dir
        op = self._ops[target]
        return FakeCommand(op[0], op[1], self._ref, options)
