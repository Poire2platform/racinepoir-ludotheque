"""Add game sessions

Revision ID: 9a1f4e5d8c20
Revises: 6f4a524a0619
Create Date: 2026-07-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "9a1f4e5d8c20"
down_revision = "6f4a524a0619"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "player_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=120), nullable=False),
        sa.Column("linked_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["linked_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("linked_user_id"),
    )
    op.create_index(op.f("ix_player_profiles_display_name"), "player_profiles", ["display_name"], unique=False)
    op.create_index(op.f("ix_player_profiles_normalized_name"), "player_profiles", ["normalized_name"], unique=False)

    op.create_table(
        "game_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("box_id", sa.Integer(), nullable=True),
        sa.Column("played_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["box_id"], ["boxes.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_game_sessions_box_id"), "game_sessions", ["box_id"], unique=False)
    op.create_index(op.f("ix_game_sessions_game_id"), "game_sessions", ["game_id"], unique=False)

    op.create_table(
        "game_session_participants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("player_profile_id", sa.Integer(), nullable=False),
        sa.Column("team_label", sa.String(length=80), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("is_winner", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["player_profile_id"], ["player_profiles.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["game_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_game_session_participants_player_profile_id"), "game_session_participants", ["player_profile_id"], unique=False)
    op.create_index(op.f("ix_game_session_participants_session_id"), "game_session_participants", ["session_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_game_session_participants_session_id"), table_name="game_session_participants")
    op.drop_index(op.f("ix_game_session_participants_player_profile_id"), table_name="game_session_participants")
    op.drop_table("game_session_participants")

    op.drop_index(op.f("ix_game_sessions_game_id"), table_name="game_sessions")
    op.drop_index(op.f("ix_game_sessions_box_id"), table_name="game_sessions")
    op.drop_table("game_sessions")

    op.drop_index(op.f("ix_player_profiles_normalized_name"), table_name="player_profiles")
    op.drop_index(op.f("ix_player_profiles_display_name"), table_name="player_profiles")
    op.drop_table("player_profiles")
