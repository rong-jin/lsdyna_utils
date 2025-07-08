"""
Author : Rong Jin, University of Kentucky
Date   : 07-08-2025
File   : runner.py – launch LS-DYNA jobs from Python

Public API
----------
run_lsdyna(kfile, *, ncpu=1, memory='256m', …)         → subprocess.CompletedProcess
    • Launch one single-core or multi-core LS-DYNA job.

run_lsdyna_batch(iterable_of_kfiles, *, max_workers=8, **kwargs)
    • Submit many *.k* files concurrently (thread pool).
    • Yields ``(Path_to_kfile, return_code)`` as each job finishes.

Tee(path)  – context-manager to duplicate stdout/stderr to a log file.

Typical usage
-------------
>>> from lsdyna_utils.runner import run_lsdyna, run_lsdyna_batch
>>> run_lsdyna("Run.k", ncpu=8, memory="4g",
...            tee="Run.log", timeout=3600)

>>> for kfile, rc in run_lsdyna_batch(Path("Ensembles").rglob("*.k"),
...                                   max_workers=12, ncpu=4):
...     print(kfile.name, "→", rc)
"""

from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from subprocess import CompletedProcess
from typing import Iterable, Iterator, Sequence, TextIO

__all__ = ["DEFAULT_EXECUTABLE", "Tee", "run_lsdyna", "run_lsdyna_batch"]

# ----------------------------------------------------------------------
# Default LS-DYNA executable – adjust once and forget elsewhere
# ----------------------------------------------------------------------
DEFAULT_EXECUTABLE: Path = Path(
    r"C:\Program Files\ANSYS Inc\v231\ansys\bin\winx64\lsdyna_dp.exe"
)

# ----------------------------------------------------------------------
# Helper 0 – duplicate stdout/stderr
# ----------------------------------------------------------------------
class Tee:
    """
    Context-managed “tee” – anything printed inside the *with* block goes
    both to terminal and *path*.

    Example
    -------
    >>> with Tee("run.log"):
    ...     print("hello")      # shows on screen *and* in run.log
    """

    def __init__(self, path: str | Path, mode: str = "w", encoding: str = "utf-8"):
        self._file: TextIO = open(path, mode, encoding=encoding)
        self._stdout: TextIO = subprocess.sys.stdout  # type: ignore[attr-defined]

    def write(self, msg: str) -> None:  # called by print(…)
        self._stdout.write(msg)
        self._file.write(msg)

    def flush(self) -> None:
        self._stdout.flush()
        self._file.flush()

    # --------------------------------------------------------------
    # context-manager API
    # --------------------------------------------------------------
    def __enter__(self) -> "Tee":
        subprocess.sys.stdout = self  # type: ignore[assignment]
        subprocess.sys.stderr = self  # mirror stderr too
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: D401
        subprocess.sys.stdout = self._stdout  # type: ignore[assignment]
        subprocess.sys.stderr = self._stdout  # restore both
        self._file.close()
        return False


# ----------------------------------------------------------------------
# Helper 1 – build LS-DYNA command list
# ----------------------------------------------------------------------
def _build_cmd(
    executable: Path,
    kfile: Path,
    ncpu: int,
    memory: str,
    dump_file: str | None = None,
) -> list[str]:
    cmd: list[str] = [
        str(executable),
        f"i={kfile}",
        f"ncpu={ncpu}",
        f"memory={memory}",
    ]
    if dump_file:
        cmd.append(f"R={dump_file}")
    return cmd


# ----------------------------------------------------------------------
# Single-job launcher
# ----------------------------------------------------------------------
def run_lsdyna(
    kfile: str | Path,
    *,
    ncpu: int = 1,
    memory: str = "256m",
    cwd: str | Path | None = None,
    executable: str | Path = DEFAULT_EXECUTABLE,
    dump_file: str | None = None,
    timeout: int | None = None,
    capture_output: bool = True,
    tee: str | Path | None = None,
    check: bool = False,
) -> CompletedProcess:
    """
    Blocking call to LS-DYNA.

    Parameters
    ----------
    kfile
        Input keyword file.
    ncpu, memory
        LS-DYNA command-line options.
    cwd
        Working directory; defaults to *kfile.parent*.
    executable
        Path to ``lsdyna_dp.exe``.
    dump_file
        Optional ``R=`` restart/dump argument.
    timeout
        Seconds before force-killing the process.
    capture_output
        If *True* → pipe stdout/stderr (kept in ``proc.stdout``).
    tee
        If given, duplicate **both** stdout & stderr to this file.
        Has no effect if ``capture_output=False``.
    check
        Forwarded to ``subprocess.run`` (“raise on non-zero rc”).

    Returns
    -------
    subprocess.CompletedProcess
    """
    kfile = Path(kfile).resolve()
    cwd_path = Path(cwd or kfile.parent).resolve()
    executable = Path(executable).expanduser().resolve()

    cmd = _build_cmd(executable, kfile, ncpu, memory, dump_file)

    if tee is not None and not capture_output:
        raise ValueError("`tee=` only makes sense when capture_output=True")

    if tee:
        with Tee(tee):
            return subprocess.run(
                cmd,
                cwd=cwd_path,
                text=True,
                capture_output=capture_output,
                timeout=timeout,
                check=check,
            )

    return subprocess.run(
        cmd,
        cwd=cwd_path,
        text=True,
        capture_output=capture_output,
        timeout=timeout,
        check=check,
    )


# ----------------------------------------------------------------------
# Batch launcher – thread pool
# ----------------------------------------------------------------------
def run_lsdyna_batch(
    kfiles: Iterable[str | Path],
    *,
    max_workers: int = 8,
    **kwargs,
) -> Iterator[tuple[Path, int]]:
    """
    Launch many LS-DYNA jobs concurrently (thread pool).

    Parameters
    ----------
    kfiles
        Iterable of *.k* paths.
    max_workers
        Number of threads (IO-bound, so threads are fine).
    **kwargs
        Forwarded verbatim to :pyfunc:`run_lsdyna`.

    Yields
    ------
    ``(kfile_path, return_code)``  as each job completes.
    """
    kpaths: list[Path] = [Path(k).resolve() for k in kfiles]

    def _worker(p: Path) -> tuple[Path, int]:
        proc = run_lsdyna(p, **kwargs)
        return p, proc.returncode

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_worker, p): p for p in kpaths}
        for fut in as_completed(futures):
            yield fut.result()
