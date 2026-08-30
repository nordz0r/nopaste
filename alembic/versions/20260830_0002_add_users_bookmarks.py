"""add users, paste authors, and bookmarks

Revision ID: 20260830_0002
Revises: 20260806_0001
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260830_0002"
down_revision: Union[str, Sequence[str], None] = "20260806_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pastes", sa.Column("author_id", sa.String(128), nullable=True))
    op.create_index("ix_pastes_author_id", "pastes", ["author_id"])
    op.create_table(
        "users",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("username", sa.String(128), nullable=False),
        sa.Column("email", sa.String(256), nullable=True),
        sa.Column("display_name", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_table(
        "bookmarks",
        sa.Column("user_id", sa.String(128), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("paste_id", sa.String(64), sa.ForeignKey("pastes.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_bookmarks_paste_id", "bookmarks", ["paste_id"])


def downgrade() -> None:
    op.drop_index("ix_bookmarks_paste_id", table_name="bookmarks")
    op.drop_table("bookmarks")
    op.drop_table("users")
    op.drop_index("ix_pastes_author_id", table_name="pastes")
    op.drop_column("pastes", "author_id")
