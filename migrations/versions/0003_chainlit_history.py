"""Create the Chainlit 2.11 SQLAlchemy data-layer schema.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY,
            identifier TEXT NOT NULL UNIQUE,
            metadata JSONB NOT NULL,
            "createdAt" TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS threads (
            id UUID PRIMARY KEY,
            "createdAt" TEXT,
            name TEXT,
            "userId" UUID,
            "userIdentifier" TEXT,
            tags TEXT[],
            metadata JSONB,
            FOREIGN KEY ("userId") REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_threads_owner ON threads ("userIdentifier", id)'
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS steps (
            id UUID PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            "threadId" UUID NOT NULL,
            "parentId" UUID,
            streaming BOOLEAN NOT NULL,
            "waitForAnswer" BOOLEAN,
            "isError" BOOLEAN,
            metadata JSONB,
            tags TEXT[],
            input TEXT,
            output TEXT,
            "createdAt" TEXT,
            command TEXT,
            start TEXT,
            "end" TEXT,
            generation JSONB,
            "showInput" TEXT,
            language TEXT,
            indent INT,
            "defaultOpen" BOOLEAN,
            modes JSONB,
            FOREIGN KEY ("threadId") REFERENCES threads(id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_steps_thread ON steps ("threadId", "createdAt")'
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS elements (
            id UUID PRIMARY KEY,
            "threadId" UUID,
            type TEXT,
            url TEXT,
            "chainlitKey" TEXT,
            name TEXT NOT NULL,
            display TEXT,
            "objectKey" TEXT,
            size TEXT,
            page INT,
            language TEXT,
            "forId" UUID,
            mime TEXT,
            props JSONB,
            FOREIGN KEY ("threadId") REFERENCES threads(id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS feedbacks (
            id UUID PRIMARY KEY,
            "forId" UUID NOT NULL,
            "threadId" UUID NOT NULL,
            value INT NOT NULL,
            comment TEXT,
            FOREIGN KEY ("threadId") REFERENCES threads(id) ON DELETE CASCADE
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS feedbacks")
    op.execute("DROP TABLE IF EXISTS elements")
    op.execute("DROP TABLE IF EXISTS steps")
    op.execute("DROP TABLE IF EXISTS threads")
    op.execute("DROP TABLE IF EXISTS users")
