"""Create phase-one persistent memory tables.

Revision ID: 0001
Revises:
Create Date: 2026-07-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        """
        CREATE TABLE user_memories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_identifier TEXT NOT NULL,
            scope TEXT NOT NULL,
            thread_id TEXT NULL,
            category TEXT NOT NULL DEFAULT 'general',
            memory_text TEXT NOT NULL,
            normalized_text TEXT NOT NULL,
            normalized_hash CHAR(64) NOT NULL,
            importance SMALLINT NOT NULL DEFAULT 5,
            confidence NUMERIC(4,3) NOT NULL DEFAULT 1.000,
            source TEXT NOT NULL,
            source_message_id TEXT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_used_at TIMESTAMPTZ NULL,
            expires_at TIMESTAMPTZ NULL,
            deleted_at TIMESTAMPTZ NULL,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            CONSTRAINT valid_memory_scope
                CHECK (scope IN ('global', 'thread')),
            CONSTRAINT thread_scope_has_thread
                CHECK (scope <> 'thread' OR thread_id IS NOT NULL),
            CONSTRAINT global_scope_has_no_thread
                CHECK (scope <> 'global' OR thread_id IS NULL),
            CONSTRAINT valid_importance CHECK (importance BETWEEN 1 AND 10),
            CONSTRAINT valid_confidence CHECK (confidence BETWEEN 0 AND 1)
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_active_user_memory
        ON user_memories (
            user_identifier, scope, COALESCE(thread_id, ''), normalized_hash
        ) WHERE deleted_at IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX idx_global_memory_lookup
        ON user_memories (user_identifier, importance DESC, updated_at DESC)
        WHERE scope = 'global' AND deleted_at IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX idx_thread_memory_lookup
        ON user_memories (
            user_identifier, thread_id, importance DESC, updated_at DESC
        ) WHERE scope = 'thread' AND deleted_at IS NULL
        """
    )
    op.execute(
        """
        CREATE TABLE user_memory_preferences (
            user_identifier TEXT PRIMARY KEY,
            memory_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            automatic_memory_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            allow_global_memory BOOLEAN NOT NULL DEFAULT TRUE,
            allow_thread_memory BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE thread_summaries (
            thread_id TEXT PRIMARY KEY,
            user_identifier TEXT NOT NULL,
            summary_text TEXT NOT NULL,
            summarized_through_message_id TEXT NULL,
            summarized_message_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_thread_summary_owner "
        "ON thread_summaries (user_identifier, thread_id)"
    )
    op.execute(
        """
        CREATE TABLE memory_audit_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_identifier TEXT NOT NULL,
            memory_id UUID NULL,
            operation TEXT NOT NULL,
            scope TEXT NULL,
            thread_id TEXT NULL,
            actor TEXT NOT NULL,
            reason TEXT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            CONSTRAINT valid_memory_operation CHECK (
                operation IN (
                    'create', 'read', 'update', 'delete', 'reject',
                    'export', 'disable', 'enable'
                )
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS memory_audit_events")
    op.execute("DROP TABLE IF EXISTS thread_summaries")
    op.execute("DROP TABLE IF EXISTS user_memory_preferences")
    op.execute("DROP TABLE IF EXISTS user_memories")
