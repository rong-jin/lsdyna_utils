"""
Author : Rong Jin, University of Kentucky
Date   : 07-08-2025
File   : kfile.py – minimal helper for patching LS-DYNA keyword (*.k) files

This module exposes one public function
---------------------------------------
modify_k_params(kfile_in, kfile_out=None, repl={})
    • Replaces the numeric value of specific *labels* in a *.k file.
    • Works on any line that looks like:   LABEL , value
      (     comma separates label and value, anything after the first
       comma is treated as the numeric part.)
    • If *kfile_out* is None the original file is overwritten in-place.

Typical usage
-------------
>>> from lsdyna_utils.kfile import modify_k_params
>>> modify_k_params("Run.k", "Run_mod.k",
...                 {"RC1": 0.0025, "RD41": 0.35, "RG": 1.155})
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence


def modify_k_params(
    kfile_in: str | Path,
    kfile_out: str | Path | None = None,
    repl: Mapping[str, float] | Sequence[tuple[str, float]] = (),
) -> Path:
    """
    Replace the value of *label,value* rows in an LS-DYNA *.k file.

    Parameters
    ----------
    kfile_in
        Path to the original keyword file.
    kfile_out
        Where to write the patched file.
        • If *None*  → overwrite *kfile_in*.
        • If a path  → write to that new file (original stays untouched).
    repl
        Mapping ``{label: new_value}`` **or** a sequence of
        ``[(label, new_value), …]``.  Labels are matched *case-sensitively*.

    Returns
    -------
    Path
        Path of the file that was written (same as *kfile_out*
        or *kfile_in* if overwritten).

    Notes
    -----
    * Only the first comma on each line is considered the label/value split.
    * If the same label appears multiple times, **all** occurrences are
      replaced.
    * Numeric values are written in scientific notation with four
      significant digits (``%.4e``) – tweak the format string if a
      different precision is required.
    """
    # --- Normalise replacements to a plain dict for O(1) look-up ----------
    pairs: dict[str, float] = dict(repl)

    # --- Read the entire file into a list of strings ----------------------
    with open(kfile_in, "r") as fh:
        lines: list[str] = fh.readlines()

    # --- Scan & patch lines in-memory ------------------------------------
    for idx, line in enumerate(lines):
        if "," not in line:
            # Skip lines that clearly cannot be “LABEL,value”
            continue

        # Split only once – anything after the first comma belongs to value
        label, _ = [frag.strip() for frag in line.split(",", maxsplit=1)]

        if label in pairs:
            # Format new value (scientific notation, 4 decimals)
            new_val = f"{pairs[label]:.4e}"
            lines[idx] = f"{label},{new_val}\n"

    # --- Decide where to write the output ---------------------------------
    out_path = Path(kfile_out or kfile_in)  # overwrite if None

    with open(out_path, "w") as fh:
        fh.writelines(lines)

    return out_path
