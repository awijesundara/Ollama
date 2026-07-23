"""Add optional pgvector embeddings and retention indexes.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("ALTER TABLE user_memories ADD COLUMN embedding vector(768)")
    op.execute(
        """
        CREATE INDEX idx_user_memories_embedding
        ON user_memories USING hnsw (embedding vector_cosine_ops)
        WHERE deleted_at IS NULL AND embedding IS NOT NULL
        """
    )
    op.execute(
        "CREATE INDEX idx_memory_expiry ON user_memories (expires_at) "
        "WHERE expires_at IS NOT NULL AND deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX idx_audit_retention ON memory_audit_events (created_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_audit_retention")
    op.execute("DROP INDEX IF EXISTS idx_memory_expiry")
    op.execute("DROP INDEX IF EXISTS idx_user_memories_embedding")
    op.execute("ALTER TABLE user_memories DROP COLUMN IF EXISTS embedding")

