"""
lsdyna_utils  ‒  Lightweight helpers for LS-DYNA

公开 API
--------
- modify_k_params  : 修改 .k 文件参数
- extract_nodout   : 提取 nodout 任意场量、时间步
"""

from importlib import metadata

# 对外暴露的主函数
from .kfile import modify_k_params          # noqa: F401
from .nodout import extract_nodout          # noqa: F401

# 可选：版本号，读取 pyproject.toml / setup.cfg 中的 project version
try:
    __version__: str = metadata.version(__name__)   # type: ignore[attr-defined]
except metadata.PackageNotFoundError:               # pragma: no cover
    __version__ = "0.0.0"

__all__ = [
    "modify_k_params",
    "extract_nodout",
    "__version__",
]
