import contextlib
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor
from typing import IO, List, Sequence, Tuple

from .reporter import Reporter


def _read_stream(stream: IO[bytes], reporter: Reporter, loglevel: int) -> str:
    ret: List[str] = []
    for s in stream:
        line = s.decode("utf-8")
        ret.append(line)
        reporter.process_output.log(loglevel, line.rstrip("\n"))

    return "".join(ret)


def run(
    cmd: Sequence[str],
    reporter: Reporter,
    stdout_loglevel: int = logging.INFO,
    stderr_loglevel: int = logging.WARNING,
) -> Tuple[int, str, str]:
    returncode: int = -1
    stdout: str = ""
    stderr: str = ""

    with contextlib.ExitStack() as stack:
        reporter.report_command(" ".join(cmd))
        proc = stack.enter_context(
            subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
