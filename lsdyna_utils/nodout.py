"""
nodout.py ── One-stop extractor for LS-DYNA *nodout* files.

Example
-------
from lsdyna_utils.nodout import extract_nodout

z = extract_nodout(
        "nodout",
        field="z_disp",
        node_ids=[101, 105, 120],
        t_start=1.0e-5,
        t_step =1.0e-6,
        n_steps=5,
        save="z_disp.csv",
)
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, Literal, Sequence

import numpy as np

_Field = Literal[
    "nodal_point",
    "x_disp",
    "y_disp",
    "z_disp",
    "x_vel",
    "y_vel",
    "z_vel",
    "x_accl",
    "y_accl",
    "z_accl",
    "x_coor",
    "y_coor",
    "z_coor",
]

# 固定宽度设置：第 1 列 10 位，其余 12 位
_BYTE0 = 10
_BYTEW = 12


def _slice_pos(field: _Field) -> slice:
    if field == "nodal_point":
        return slice(0, _BYTE0)
    idx = [
        "x_disp",
        "y_disp",
        "z_disp",
        "x_vel",
        "y_vel",
        "z_vel",
        "x_accl",
        "y_accl",
        "z_accl",
        "x_coor",
        "y_coor",
        "z_coor",
    ].index(field)
    start = _BYTE0 + idx * _BYTEW
    return slice(start, start + _BYTEW)


# ---------------------- 公开函数 ----------------------
def extract_nodout(
    nodout: str | Path,
    *,
    field: _Field = "z_disp",
    node_ids: Sequence[int] | None = None,
    # 时间相关
    t_total: float | None = None,
    t_start: float = 0.0,
    t_step: float | None = None,
    n_steps: int | None = None,
    # 输出
    save: str | Path | None = None,
) -> np.ndarray:
    """
    通用提取函数：返回 (time, node) 数组。

    只需告诉我想要：
    - 哪个字段 (field)
    - 哪些节点 (node_ids=None 表示全部)
    - 哪些时间步 (t_start, t_step, n_steps) —— 不想管就都给 None → 全时间

    Parameters
    ----------
    nodout : str | Path
        nodout 文件路径
    field : str
        提取的场量
    node_ids : list[int] | None
        关心的节点序号。为 None 则保留文件顺序全部节点
    t_total : float | None
        仿真总时间；若给出则可自动计算 dt
    t_start : float
        起始时间
    t_step : float | None
        采样间隔；不给则连续读取
    n_steps : int | None
        要读取的步数；不给则直到文件结束
    save : str | Path | None
        若给出，则将结果保存 csv/txt

    Returns
    -------
    np.ndarray
        shape = (n_steps, n_nodes)
    """
    path = Path(nodout).resolve()
    slc = _slice_pos(field)

    # ---------- 预扫描：确定每个时间块行数、dt ----------
    with open(path, "r") as fh:
        first_line = fh.readline()
        if "time=" not in first_line:
            raise RuntimeError("nodout format not recognised — missing 'time='")
        # 每块行数 = 直到遇到空行或下一个 "time="
        start_pos = fh.tell()
        n_lines_block = 0
        while True:
            ln = fh.readline()
            if not ln or "time=" in ln:
                break
            n_lines_block += 1
        fh.seek(start_pos)
        block_bytes = n_lines_block + 1  # + header
        lines_per_block = n_lines_block

        # 时间步长
        if t_total is not None:
            # 文件末行的 time= t_total
            dt = t_total / (blocks_in_file := _count_blocks(path, "time=") - 1)
        else:
            # 粗算 — 取前两个 time=
            fh.seek(0)
            t0 = float(_get_time(fh.readline()))
            while True:
                ln = fh.readline()
                if "time=" in ln:
                    t1 = float(_get_time(ln))
                    break
            dt = t1 - t0

    # ---------- 节点行号过滤 ----------
    if node_ids is not None:
        node_ids_set = set(node_ids)

    # ---------- 时间步范围 ----------
    first_idx = int(round(t_start / dt))
    step_span = int(round((t_step or dt) / dt))
    n_steps = (
        n_steps
        if n_steps is not None
        else math.inf  # 直到文件结束
    )

    # ---------- 主循环 ----------
    data: list[np.ndarray] = []
    with open(path, "r") as fh:
        # 跳到 first_idx
        _skip_n_blocks(fh, first_idx, lines_per_block)
        for _ in range(int(n_steps)):
            header = fh.readline()
            if not header:
                break
            # 读该时间块
            rows: list[float] = []
            nodes_in_block: list[int] = []

            for _ in range(lines_per_block):
                line = fh.readline()
                if not line or "time=" in line:
                    break
                node_id = int(line[slc_of("nodal_point")].strip())
                if (node_ids is None) or (node_id in node_ids_set):
                    val_str = line[slc].strip()
                    rows.append(float(_fix(val_str)))
                    nodes_in_block.append(node_id)

            if not rows:
                break
            data.append(np.asarray(rows))

            # 跳过中间时间块
            _skip_n_blocks(fh, step_span - 1, lines_per_block)

    arr = np.vstack(data)
    if save:
        np.savetxt(save, arr, delimiter=",", fmt="%.6e")
    return arr


# ---------------------- 内部小工具 ----------------------
def _count_blocks(path: Path, key: str) -> int:
    with open(path, "r") as fh:
        return sum(1 for ln in fh if key in ln)


def _get_time(line: str) -> float:
    # "... time= 1.20000E-05"
    return float(line.split("time=")[1])


def _skip_n_blocks(fh, n: int, lines_per_block: int) -> None:
    for _ in range(n):
        # 跳 header + 内容
        fh.readline()
        for _ in range(lines_per_block):
            fh.readline()


def slc_of(fld: _Field) -> slice:
    return _slice_pos(fld)


def _fix(s: str) -> str:
    """确保科学计数法字符串包含 e/E。"""
    if "e" in s.lower():
        return s
    for i in range(1, len(s)):
        if s[i] in "+-":
            return f"{s[:i]}e{s[i:]}"
    return s
