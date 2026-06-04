"""drop location name unique constraint

Revision ID: f3a8c2d91b04
Revises: e1ad25e6055a
Create Date: 2026-05-30 19:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a8c2d91b04"
down_revision: str | Sequence[str] | None = "e1ad25e6055a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    unique_constraints = inspector.get_unique_constraints("location")
    has_name_unique = any("name" in constraint.get("column_names", []) for constraint in unique_constraints)
    if not has_name_unique:
        return

    # SQLite cannot drop unnamed unique constraints; recreate the table instead.
    op.execute(
        """
        CREATE TABLE location_new (
            id INTEGER NOT NULL,
            name VARCHAR NOT NULL,
            city VARCHAR,
            state VARCHAR,
            postal_code VARCHAR,
            email VARCHAR,
            PRIMARY KEY (id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO location_new (id, name, city, state, postal_code, email)
        SELECT id, name, city, state, postal_code, email
        FROM location
        """
    )
    op.execute("DROP TABLE location")
    op.execute("ALTER TABLE location_new RENAME TO location")
    op.create_index(op.f("ix_location_id"), "location", ["id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    unique_constraints = inspector.get_unique_constraints("location")
    has_name_unique = any("name" in constraint.get("column_names", []) for constraint in unique_constraints)
    if has_name_unique:
        return

    op.execute(
        """
        CREATE TABLE location_new (
            id INTEGER NOT NULL,
            name VARCHAR NOT NULL,
            city VARCHAR,
            state VARCHAR,
            postal_code VARCHAR,
            email VARCHAR,
            PRIMARY KEY (id),
            UNIQUE (name)
        )
        """
    )
    op.execute(
        """
        INSERT INTO location_new (id, name, city, state, postal_code, email)
        SELECT id, name, city, state, postal_code, email
        FROM location
        """
    )
    op.execute("DROP TABLE location")
    op.execute("ALTER TABLE location_new RENAME TO location")
    op.create_index(op.f("ix_location_id"), "location", ["id"], unique=False)
