"""Initial PostgreSQL schema for the playbook store.

Revision ID: 001
Revises:
Create Date: 2026-05-29

Squashed, Postgres-native baseline. pbook stores curated advice and
LLM-extracted pitfalls in a single ``entries`` table, tracks ingested
Claude Code sessions in ``ingested_sessions``, and records per-experience
provenance in ``entry_sources``. Embeddings are stored as pgvector
``vector`` columns and ranked with the cosine distance operator, backed
by an HNSW index.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

# Embedding dimensionality (OpenAI text-embedding-3-small).
EMBEDDING_DIM = 1536


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "entries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("tags_json", sa.Text, nullable=False),
        sa.Column(
            "entry_type", sa.String, nullable=False, server_default="curated",
        ),
        sa.Column(
            "source_project", sa.String, nullable=False, server_default="",
        ),
        sa.Column(
            "source_task_id", sa.String, nullable=False, server_default="",
        ),
        sa.Column(
            "needs_review", sa.Boolean, nullable=False, server_default=sa.text("false"),
        ),
        sa.Column(
            "helpful_count", sa.Integer, nullable=False, server_default=sa.text("0"),
        ),
        sa.Column(
            "harmful_count", sa.Integer, nullable=False, server_default=sa.text("0"),
        ),
        sa.Column(
            "retrieval_count", sa.Integer, nullable=False, server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column(
            "rejected", sa.Boolean, nullable=False, server_default=sa.text("false"),
        ),
        sa.Column("rejection_reason", sa.Text, nullable=True),
    )
    op.create_index("ix_entries_source_project", "entries", ["source_project"])
    op.create_index("ix_entries_entry_type", "entries", ["entry_type"])
    op.create_index(
        "ix_entries_embedding_hnsw",
        "entries",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "ingested_sessions",
        sa.Column("session_id", sa.Text, primary_key=True),
        sa.Column("project_name", sa.Text, nullable=False, server_default=""),
        sa.Column(
            "ingested_at",
            sa.DateTime,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "experiences_found", sa.Integer, nullable=False, server_default=sa.text("0"),
        ),
        sa.Column(
            "entries_created", sa.Integer, nullable=False, server_default=sa.text("0"),
        ),
        sa.Column(
            "status", sa.Text, nullable=False, server_default="completed",
        ),
        sa.Column("workflow_id", sa.Text, nullable=True),
        sa.Column("run_id", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "entry_sources",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "entry_id",
            sa.Integer,
            sa.ForeignKey("entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_id", sa.Text, nullable=False, server_default=""),
        sa.Column("project_name", sa.Text, nullable=False, server_default=""),
        sa.Column("experience_hash", sa.Text, nullable=True),
        sa.Column("source_context", sa.Text, nullable=False, server_default=""),
        sa.Column(
            "source_context_embedding", Vector(EMBEDDING_DIM), nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "entry_id", "session_id", "experience_hash",
            name="uq_entry_sources_entry_session_hash",
        ),
    )
    op.create_index("ix_entry_sources_session_id", "entry_sources", ["session_id"])
    op.create_index("ix_entry_sources_entry_id", "entry_sources", ["entry_id"])


def downgrade() -> None:
    op.drop_index("ix_entry_sources_entry_id", table_name="entry_sources")
    op.drop_index("ix_entry_sources_session_id", table_name="entry_sources")
    op.drop_table("entry_sources")
    op.drop_table("ingested_sessions")
    op.drop_index("ix_entries_embedding_hnsw", table_name="entries")
    op.drop_index("ix_entries_entry_type", table_name="entries")
    op.drop_index("ix_entries_source_project", table_name="entries")
    op.drop_table("entries")
