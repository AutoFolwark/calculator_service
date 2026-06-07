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


def _name_unique_constraints(inspector: sa.Inspector) -> list[dict]:
    return [
        constraint
        for constraint in inspector.get_unique_constraints("location")
        if "name" in constraint.get("column_names", [])
    ]


def _recreate_location_table(*, with_name_unique: bool) -> None:
    unique_clause = ",\n            UNIQUE (name)" if with_name_unique else ""
    op.execute(
        f"""
        CREATE TABLE location_new (
            id INTEGER NOT NULL,
            name VARCHAR NOT NULL,
            city VARCHAR,
            state VARCHAR,
            postal_code VARCHAR,
            email VARCHAR,
            PRIMARY KEY (id){unique_clause}
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


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    name_unique_constraints = _name_unique_constraints(inspector)
    if not name_unique_constraints:
        return

    if bind.dialect.name == "postgresql":
        for constraint in name_unique_constraints:
            op.drop_constraint(constraint["name"], "location", type_="unique")
        return

    # SQLite cannot drop unnamed unique constraints; recreate the table instead.
    op.execute("PRAGMA foreign_keys=OFF")
    try:
        _recreate_location_table(with_name_unique=False)
    finally:
        op.execute("PRAGMA foreign_keys=ON")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _name_unique_constraints(inspector):
        return

    if bind.dialect.name == "postgresql":
        op.create_unique_constraint("location_name_key", "location", ["name"])
        return

    op.execute("PRAGMA foreign_keys=OFF")
    try:
        _recreate_location_table(with_name_unique=True)
    finally:
        op.execute("PRAGMA foreign_keys=ON")
