"""
输入：
- 应用配置中的 `database_url`，以及 SQLAlchemy 创建出的数据库引擎。
- 应用启动阶段触发的建表与 SQLite 补列动作。
输出：
- 导出数据库引擎、会话工厂和数据库初始化函数。
- 在 SQLite 场景下，会按需补齐普通记录、批量记录和安全回复记录缺失的历史字段列。
作用：
- 这个文件负责把配置转换成可用的数据库连接，并在启动时完成最基础的表结构准备与轻量兼容迁移。
"""
from sqlalchemy import Engine, create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.models import Base


def build_engine(settings: Settings) -> Engine:
    """
    输入：
    - settings：应用运行配置，至少包含 `database_url`。
    输出：
    - 返回一个可供 SQLAlchemy ORM 复用的数据库引擎。
    作用：
    - 根据当前数据库类型构造连接，并在 SQLite 下开启跨线程访问所需的连接参数。
    """

    connect_args: dict[str, object] = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(settings.database_url, connect_args=connect_args, future=True)


def build_session_factory(engine: Engine) -> sessionmaker:
    """
    输入：
    - engine：已经初始化完成的 SQLAlchemy 数据库引擎。
    输出：
    - 返回一个用于按请求创建数据库会话的 `sessionmaker` 工厂。
    作用：
    - 统一项目里 ORM 会话的创建策略，避免不同入口使用不一致的事务配置。
    """

    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db(engine: Engine) -> None:
    """
    输入：
    - engine：当前应用使用的数据库引擎。
    输出：
    - 创建 ORM 已知表结构；在 SQLite 下按需补齐历史兼容列。
    作用：
    - 让应用在没有完整迁移系统的前提下，仍能随着字段演进平滑读取旧库并保存新增过程数据。
    """

    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "sqlite":
        inspector = inspect(engine)
        consultation_columns = {column["name"] for column in inspector.get_columns("consultation_records")}
        _ensure_sqlite_column(
            engine,
            consultation_columns,
            "consultation_records",
            "expert_annotation",
            "TEXT NOT NULL DEFAULT ''",
        )
        _ensure_sqlite_column(
            engine,
            consultation_columns,
            "consultation_records",
            "rag_ready",
            "TEXT NOT NULL DEFAULT 'pending'",
        )
        _ensure_sqlite_column(
            engine,
            consultation_columns,
            "consultation_records",
            "sample_reason",
            "TEXT NOT NULL DEFAULT ''",
        )
        _ensure_sqlite_column(
            engine,
            consultation_columns,
            "consultation_records",
            "sample_tags_json",
            "JSON NOT NULL DEFAULT '{}'",
        )
        _ensure_sqlite_column(
            engine,
            consultation_columns,
            "consultation_records",
            "planner_labels_json",
            "JSON NOT NULL DEFAULT '{}'",
        )
        _ensure_sqlite_column(
            engine,
            consultation_columns,
            "consultation_records",
            "evaluation_json",
            "JSON NOT NULL DEFAULT '{}'",
        )
        _ensure_sqlite_column(
            engine,
            consultation_columns,
            "consultation_records",
            "sample_snapshot_json",
            "JSON NOT NULL DEFAULT '{}'",
        )
        _ensure_sqlite_column(
            engine,
            consultation_columns,
            "consultation_records",
            "source_annotations_json",
            "JSON NOT NULL DEFAULT '[]'",
        )
        _ensure_sqlite_column(
            engine,
            consultation_columns,
            "consultation_records",
            "response_versions_json",
            "JSON NOT NULL DEFAULT '[]'",
        )
        _ensure_sqlite_column(
            engine,
            consultation_columns,
            "consultation_records",
            "batch_session_id",
            "INTEGER",
        )
        _ensure_sqlite_column(
            engine,
            consultation_columns,
            "consultation_records",
            "batch_item_id",
            "INTEGER",
        )
        batch_item_columns = {column["name"] for column in inspector.get_columns("batch_session_items")}
        _ensure_sqlite_column(
            engine,
            batch_item_columns,
            "batch_session_items",
            "rag_ready",
            "TEXT NOT NULL DEFAULT 'pending'",
        )
        _ensure_sqlite_column(
            engine,
            batch_item_columns,
            "batch_session_items",
            "sample_reason",
            "TEXT NOT NULL DEFAULT ''",
        )
        _ensure_sqlite_column(
            engine,
            batch_item_columns,
            "batch_session_items",
            "sample_tags_json",
            "JSON NOT NULL DEFAULT '{}'",
        )
        _ensure_sqlite_column(
            engine,
            batch_item_columns,
            "batch_session_items",
            "planner_labels_json",
            "JSON NOT NULL DEFAULT '{}'",
        )
        _ensure_sqlite_column(
            engine,
            batch_item_columns,
            "batch_session_items",
            "evaluation_json",
            "JSON NOT NULL DEFAULT '{}'",
        )
        _ensure_sqlite_column(
            engine,
            batch_item_columns,
            "batch_session_items",
            "sample_snapshot_json",
            "JSON NOT NULL DEFAULT '{}'",
        )
        safety_record_columns = {column["name"] for column in inspector.get_columns("safety_reply_records")}
        _ensure_sqlite_column(
            engine,
            safety_record_columns,
            "safety_reply_records",
            "selected_response_source",
            "TEXT NOT NULL DEFAULT ''",
        )
        _ensure_sqlite_column(
            engine,
            safety_record_columns,
            "safety_reply_records",
            "selected_response_source_label",
            "TEXT NOT NULL DEFAULT ''",
        )
        _ensure_sqlite_column(
            engine,
            safety_record_columns,
            "safety_reply_records",
            "safe_response_candidates_json",
            "JSON NOT NULL DEFAULT '[]'",
        )
        _ensure_sqlite_column(
            engine,
            safety_record_columns,
            "safety_reply_records",
            "expert_annotation",
            "TEXT NOT NULL DEFAULT ''",
        )
        _ensure_sqlite_column(
            engine,
            safety_record_columns,
            "safety_reply_records",
            "sample_snapshot_json",
            "JSON NOT NULL DEFAULT '{}'",
        )
        _ensure_sqlite_column(
            engine,
            safety_record_columns,
            "safety_reply_records",
            "source_annotations_json",
            "JSON NOT NULL DEFAULT '[]'",
        )
        _ensure_sqlite_column(
            engine,
            safety_record_columns,
            "safety_reply_records",
            "response_versions_json",
            "JSON NOT NULL DEFAULT '[]'",
        )


def _ensure_sqlite_column(
    engine: Engine,
    current_columns: set[str],
    table_name: str,
    column_name: str,
    definition: str,
) -> None:
    """
    输入：
    - engine：当前 SQLite 数据库引擎。
    - current_columns：目标表当前已存在的列名集合。
    - table_name / column_name / definition：待补齐的列名及其 SQL 定义。
    输出：
    - 如果目标列缺失，则执行一次 `ALTER TABLE ... ADD COLUMN ...`。
    作用：
    - 为 SQLite 提供最小化的启动时补列能力，保证新增字段在旧数据库上也能立刻可用。
    """

    if column_name in current_columns:
        return
    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"))
    current_columns.add(column_name)
