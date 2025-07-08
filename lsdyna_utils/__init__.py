"""
Author : Rong Jin, University of Kentucky
Date   : 07-08-2025
Package: lsdyna_utils  ––  for LS-DYNA workflows
===================================================================

Public API
----------
modify_k_params(kfile_in, kfile_out=None, repl=…)
    Patch *label,value* rows inside any LS-DYNA *.k* file.

extract_nodout(nodout, *, field="z_disp", …)
    Pure line-number extractor (with optional physical-time resampling).

run_lsdyna(kfile, *, ncpu=1, memory='256m', …)
    Launch a single LS-DYNA job and return :class:`subprocess.CompletedProcess`.

run_lsdyna_batch(iterable_of_kfiles, *, max_workers=8, **kwargs)
    Submit many jobs concurrently (thread pool); yields ``(Path, rc)``.

Tee(path)
    Context-manager that duplicates *print()* output to both terminal
    **and** a log file.

__version__
    Dynamically read from package metadata (falls back to '0.0.0').
"""

from importlib import metadata

# ------------------------------------------------------------------
# Re-export public helpers from sub-modules
# ------------------------------------------------------------------
from .kfile import modify_k_params           # noqa: F401
from .nodout import extract_nodout           # noqa: F401
from .runner import Tee, run_lsdyna, run_lsdyna_batch   # noqa: F401

# ------------------------------------------------------------------
# Optional semantic version (read from pyproject / setup.cfg)
# ------------------------------------------------------------------
try:
    __version__: str = metadata.version(__name__)  # type: ignore[attr-defined]
except metadata.PackageNotFoundError:              # pragma: no cover
    __version__ = "0.0.0"

# ------------------------------------------------------------------
# What gets imported by `from lsdyna_utils import *`
# ------------------------------------------------------------------
__all__ = [
    "modify_k_params",
    "extract_nodout",
    "run_lsdyna",
    "run_lsdyna_batch",
    "Tee",
    "__version__",
]

