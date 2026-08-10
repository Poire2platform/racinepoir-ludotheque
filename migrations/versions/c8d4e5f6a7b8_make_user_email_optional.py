"""Make user email optional

Revision ID: c8d4e5f6a7b8
Revises: b7c3d4e5f6a7
"""

from alembic import op
import sqlalchemy as sa


revision = "c8d4e5f6a7b8"
down_revision = "b7c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE users SET email = NULL WHERE email = ''")
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "email",
            existing_type=sa.String(length=255),
            nullable=True,
        )


def downgrade():
    users = sa.table(
        "users",
        sa.column("id", sa.Integer()),
        sa.column("email", sa.String(length=255)),
    )
    connection = op.get_bind()
    missing_ids = connection.execute(
        sa.select(users.c.id).where(users.c.email.is_(None))
    ).scalars()
    for user_id in missing_ids:
        connection.execute(
            users.update()
            .where(users.c.id == user_id)
            .values(email=f"absent-{user_id}@invalid.local")
        )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "email",
            existing_type=sa.String(length=255),
            nullable=False,
        )
