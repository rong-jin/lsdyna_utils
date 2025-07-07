"""
kfile.py ── Minimal helpers to patch LS-DYNA keyword files (.k)

Usage
-----
from lsdyna_utils.kfile import modify_k_params
modify_k_params("Run.k", "Run_mod.k", {"RC1": 0.002, "RD41": 0.35})
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
    用新数值替换 .k 文件中的指定 label, value 行。

    Parameters
    ----------
    kfile_in : str | Path
        输入 .k 文件
    kfile_out : str | Path | None
        输出文件；若为 None 则原地覆盖
    repl : dict[str, float] 或 list[(label, value)]
        需要替换的键值对，例如 {"RC1": 0.003, "RG": 1.15}

    Returns
    -------
    Path
        写出的文件路径
    """
    pairs = dict(repl)
    lines: list[str]
    with open(kfile_in, "r") as fh:
        lines = fh.readlines()

    for idx, line in enumerate(lines):
        if "," in line:
            lbl, _ = [s.strip() for s in line.split(",", 1)]
            if lbl in pairs:
                lines[idx] = f"{lbl},{pairs[lbl]:.6e}\n"

    out = Path(kfile_out or kfile_in)
    with open(out, "w") as fh:
        fh.writelines(lines)
    return out
