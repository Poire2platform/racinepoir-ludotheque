"""Add game ratings

Revision ID: b7c3d4e5f6a7
Revises: 9a1f4e5d8c20
"""

from alembic import op
import sqlalchemy as sa


revision = "b7c3d4e5f6a7"
down_revision = "9a1f4e5d8c20"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "game_ratings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("score_percent", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("score_percent >= 0 AND score_percent <= 100", name="ck_game_ratings_score_percent"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", "user_id", name="uq_game_ratings_game_user"),
    )
    op.create_index(op.f("ix_game_ratings_game_id"), "game_ratings", ["game_id"], unique=False)
    op.create_index(op.f("ix_game_ratings_user_id"), "game_ratings", ["user_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_game_ratings_user_id"), table_name="game_ratings")
    op.drop_index(op.f("ix_game_ratings_game_id"), table_name="game_ratings")
    op.drop_table("game_ratings")
