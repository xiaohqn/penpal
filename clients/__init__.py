"""
输入：
- 当前 Python 进程的模块搜索路径，以及 `penpal/backend/clients` 目录本身的客户端实现文件。
输出：
- 暴露一个根级 `clients` 包，让 `from clients...` 形式的导入在 `penpal` 根目录启动时也能解析到
  `penpal/backend/clients` 下的真实客户端实现。
作用：
- 这个 shim 包用于兼容直接粘贴过来的安全链路脚本和 service。
  这些文件保留了原项目里的 `from clients...` 导入方式；这里通过包路径映射，
  让它们在不改核心实现的前提下同时支持从根目录和 `backend` 目录启动。
"""
from pathlib import Path

# 与根级 `app` shim 一样，这里把导入目标稳定映射到 `backend/clients`，
# 避免同一套安全脚本因为启动目录不同而出现 `ModuleNotFoundError: clients`。
_BACKEND_CLIENTS_DIR = Path(__file__).resolve().parents[1] / "backend" / "clients"
__path__ = [str(_BACKEND_CLIENTS_DIR)]

