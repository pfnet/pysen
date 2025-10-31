import contextlib
import logging
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import IO, List, Optional, Sequence, Tuple

from .reporter import Reporter


def _read_stream(stream: Optional[IO[str]], reporter: Reporter, loglevel: int) -> str:
    if stream is None:
        return ""

    ret: List[str] = []
    for line in stream:
        ret.append(line)
        reporter.process_output.log(loglevel, line.rstrip("\n"))

    return "".join(ret)


def add_python_executable(*cmd: str) -> Sequence[str]:
    return [sys.executable, "-m"] + list(cmd)


def run(
    cmd: Sequence[str],
    reporter: Reporter,
    stdout_loglevel: int = logging.INFO,
    stderr_loglevel: int = logging.WARNING,
    encoding: Optional[str] = None,
) -> Tuple[int, str, str]:
    # NOTE: As pysen doesn't configure `sys.stdout` with `errors=ignore` option,
    # it may cause an error when unsupported characters in an environment are
    # going to be printed.
    # As such, `run` method returns strings of printable characters in the environment
    # so that pysen doesn't need to reconfigure `sys.stdout`.
    encoding = encoding or sys.stdout.encoding

    returncode: int = -1
    stdout: str = ""
    stderr: str = ""

    with contextlib.ExitStack() as stack:
        reporter.report_command(" ".join(cmd))
        proc = stack.enter_context(
            subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding=encoding,
                universal_newlines=True,
                errors="ignore",
            )
        )
        try:
            pool = stack.enter_context(ThreadPoolExecutor(max_workers=2))
            stdout_task = pool.submit(
                _read_stream, proc.stdout, reporter, stdout_loglevel
            )
            stderr_task = pool.submit(
                _read_stream, proc.stderr, reporter, stderr_loglevel
            )

            proc.wait()

            stdout = stdout_task.result()
            stderr = stderr_task.result()
            returncode = proc.returncode
        except Exception:
            proc.kill()
            raise

    return returncode, stdout, stderr
