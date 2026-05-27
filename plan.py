"""
输入：
- `penpal/backend/plan.py` 中定义的人格、风格轴和导出函数。
输出：
- 在 `penpal` 根目录提供一个兼容旧导入路径的 `plan` 模块，向外复用 `backend.plan` 的全部导出。
作用：
- 安全链路之外，部分后端适配代码仍然保留了原来的 `from plan import ...` 写法。
  这个 shim 文件让这些导入在根目录运行时也能指向 `backend/plan.py`，避免为了迁移目录结构
  再去改动已经对齐过的业务实现。
"""

# 直接复用 `backend.plan` 的公开导出，保证根目录导入和 `backend` 目录导入看到的是同一套人格配置。
from backend.plan import *  # noqa: F401,F403
