"""
输入：
- 当前 Python 进程的模块搜索路径，以及 `penpal/backend/app` 目录本身的文件结构。
输出：
- 暴露一个根级 `app` 包，让 `from app...` 形式的导入在 `penpal` 根目录启动时也能解析到
  `penpal/backend/app` 下的真实实现。
作用：
- 这个 shim 包专门解决 `penpal` 从不同工作目录启动时的导入兼容问题。
  原始后端代码大量使用 `from app...` 的绝对导入；保留这些实现不改的前提下，
  这里通过重写包搜索路径，把根目录导入和 `backend` 目录导入统一到同一套后端代码上。
"""
from pathlib import Path

# 把根级 `app` 包映射到 `backend/app`，这样无论当前工作目录是 `penpal` 还是 `penpal/backend`，
# 现有的 `from app...` 导入都能落到同一份后端实现，避免为了兼容不同启动方式大规模改业务代码。
_BACKEND_APP_DIR = Path(__file__).resolve().parents[1] / "backend" / "app"
__path__ = [str(_BACKEND_APP_DIR)]

