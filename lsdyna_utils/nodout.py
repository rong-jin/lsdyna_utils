"""
Author : Rong Jin, University of Kentucky
Date   : 07-08-2025
File   : nodout.py – line-number-based extractor for LS-DYNA *nodout* files

Public API
----------
extract_nodout(nodout, *, field="z_disp", start_line=…, …)
    • Works purely with line numbers:  *start_line* / *line_offset*
      / *range_length*.
    • Optionally performs an extra “physical-time” resampling if you
      supply *total_time* + *start_rt_value* + … parameters.
    • Always returns a NumPy array and can optionally write a CSV file.
"""


from __future__ import annotations

from pathlib import Path
from typing import Literal, Sequence

import numpy as np

# ────────────────────────────────────────────────────────────────
# Constants & typing helpers
# ────────────────────────────────────────────────────────────────
_Field = Literal[
    "nodal_point",
    "x_disp", "y_disp", "z_disp",
    "x_vel",  "y_vel",  "z_vel",
    "x_accl", "y_accl", "z_accl",
    "x_coor", "y_coor", "z_coor",
]

_BYTE0 = 10
_BYTEW = 12

_FIELDS: list[str] = [
    "nodal_point",
    "x_disp", "y_disp", "z_disp",
    "x_vel",  "y_vel",  "z_vel",
    "x_accl", "y_accl", "z_accl",
    "x_coor", "y_coor", "z_coor",
]


# ────────────────────────────────────────────────────────────────
# Internal helpers
# ────────────────────────────────────────────────────────────────
def _slice_pos(field: _Field) -> slice:
    """Fixed-width slice location for *field*."""
    if field == "nodal_point":
        return slice(0, _BYTE0)
    idx = _FIELDS.index(field)
    start = _BYTE0 + (idx - 1) * _BYTEW
    return slice(start, start + _BYTEW)


def _fix_scientific(s: str) -> str:
    """Insert 'e' if a mantissa/exponent string comes without it."""
    if "e" in s.lower():
        return s
    for i in range(1, len(s)):
        if s[i] in "+-":
            return f"{s[:i]}e{s[i:]}"
    return s


# ────────────────────────────────────────────────────────────────
# Public extractor
# ────────────────────────────────────────────────────────────────
def extract_nodout(
    nodout: str | Path,
    *,
    # ---- mandatory line-number settings ----
    field: _Field = "z_disp",
    start_line: int,
    line_offset: int,
    range_length: int,
    # ---- optional physical-time resampling ----
    node_num: int | None = None,
    total_time: float | None = None,
    start_rt_value: float | None = None,
    rt_step: float | None = None,
    num_time_steps: int | None = None,
    n_extract: int | None = None,
    # ---- outputs ----
    save_csv: str | Path | None = None,
    save_txt: str | Path | None = None,
) -> np.ndarray:
    """
    Extract *field* from a nodout file that has **no** “time=” headers.

    Mode 1 (line numbers only)
    --------------------------
    ▶ Provide ``start_line``, ``line_offset``, ``range_length`` ➜ return
      array shape ``(n_blocks, range_length)``.

    Mode 2 (line numbers + physical-time resampling)
    -----------------------------------------------
    ▶ Additionally provide
      ``node_num, total_time, start_rt_value, rt_step,
      num_time_steps, n_extract`` ➜ return array shape
      ``(num_time_steps, n_extract)``.

    Output
    ------
    • ``save_csv``  – writes comma-separated file (NumPy ``delimiter=","``).  
    • ``save_txt``  – writes space-separated plain text.  
    • Pass neither to skip file output, or pass both to save twice.
    """
    # 0) sanity checks
    if field not in _FIELDS:
        raise ValueError(f"field={field!r} invalid – choose one of {_FIELDS}")

    col = _slice_pos(field)
    path = Path(nodout).resolve()

    # 1) Basic line-number extraction → arr shape (n_blocks, range_length)
    with open(path, "r") as fh:
        lines = fh.readlines()

    blocks: list[list[float]] = []
    cur = start_line
    while cur + range_length - 1 <= len(lines):
        vals = [
            float(_fix_scientific(lines[i][col].strip()))
            for i in range(cur - 1, cur + range_length - 1)
        ]
        blocks.append(vals)
        cur += line_offset
    arr = np.asarray(blocks)

    # 2) Optional physical-time resampling
    if total_time is not None:
        required = [node_num, start_rt_value, rt_step, num_time_steps, n_extract]
        if any(v is None for v in required):
            raise ValueError(
                "Resampling needs node_num, total_time, start_rt_value, "
                "rt_step, num_time_steps, n_extract."
            )
        if node_num != range_length:
            raise ValueError("node_num must equal range_length.")

        dt = total_time / (arr.shape[0] - 1) if arr.shape[0] > 1 else total_time
        idx_start = round(start_rt_value / dt)
        idx_step  = round(rt_step / dt)

        arr = np.vstack([
            arr[idx_start + k * idx_step, : n_extract]
            for k in range(num_time_steps)  # type: ignore[arg-type]
        ])

    # 3) Optional file output(s)
    if save_csv:
        np.savetxt(save_csv, arr, delimiter=",", fmt="%.6e")
    if save_txt:
        np.savetxt(save_txt, arr, delimiter=" ", fmt="%.6e")

    return arr
