from sqlalchemy import Engine, create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.models import Base


def build_engine(settings: Settings) -> Engine:
    connect_args: dict[str, object] = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(settings.database_url, connect_args=connect_args, future=True)


def build_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "sqlite":
        inspector = inspect(engine)
        consultation_columns = {column["name"] for column in inspector.get_columns("consultation_records")}
        _ensure_sqlite_column(
            engine,
            consultation_columns,
            "consultation_records",
            "counselor_id",
            "TEXT NOT NULL DEFAULT 'default'",
        )
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
            "risk_assessment_json",
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
            "workspace_task_id",
            "INTEGER",
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
        batch_session_columns = {column["name"] for column in inspector.get_columns("batch_sessions")}
        _ensure_sqlite_column(
            engine,
            batch_session_columns,
            "batch_sessions",
            "counselor_id",
            "TEXT NOT NULL DEFAULT 'default'",
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
            "risk_assessment_json",
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
        _ensure_sqlite_column(
            engine,
            batch_item_columns,
            "batch_session_items",
            "mail_thread_id",
            "INTEGER",
        )
        _ensure_sqlite_column(
            engine,
            batch_item_columns,
            "batch_session_items",
            "context_json",
            "JSON NOT NULL DEFAULT '{}'",
        )
        user_letter_columns = {column["name"] for column in inspector.get_columns("user_letters")}
        _ensure_sqlite_column(
            engine,
            user_letter_columns,
            "user_letters",
            "response_preference",
            "TEXT NOT NULL DEFAULT ''",
        )
        _ensure_sqlite_column(
            engine,
            user_letter_columns,
            "user_letters",
            "assigned_counselor_id",
            "TEXT",
        )


def _ensure_sqlite_column(
    engine: Engine,
    current_columns: set[str],
    table_name: str,
    column_name: str,
    definition: str,
) -> None:
    if column_name in current_columns:
        return
    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"))
    current_columns.add(column_name)
