"""
输入：
- `planner_actor_adapter.py` 通过顶层 `plan` 模块读取的人格矩阵、风格轴定义和辅助函数。
输出：
- 对外重新导出 `app.adapters.plan` 中的人格配置与工具函数。
作用：
- 为 `penpal/backend` 提供一个本地顶层 `plan.py` 入口，避免运行时再依赖仓库外或其它目录中的同名模块。
"""

from app.adapters.plan import (  # noqa: F401
    GENERATOR_PROMPT,
    PERSONAS,
    PLANNER_PROMPT,
    STYLE_AXES_DEF,
    STYLE_VALUE_ALIASES,
    get_all_persona_names,
    get_persona_style_config,
    normalize_style_value,
    run_multi_agent_pipeline,
)
