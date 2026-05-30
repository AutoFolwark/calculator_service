"""drop exchange_rate table

Revision ID: a7b3c4d5e6f7
Revises: f3a8c2d91b04
Create Date: 2026-05-30 20:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7b3c4d5e6f7"
down_revision: str | Sequence[str] | None = "f3a8c2d91b04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(op.f("ix_exchange_rate_id"), table_name="exchange_rate")
    op.drop_table("exchange_rate")


def downgrade() -> None:
    import sqlalchemy as sa

    op.create_table(
        "exchange_rate",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rate", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_exchange_rate_id"), "exchange_rate", ["id"], unique=False)
