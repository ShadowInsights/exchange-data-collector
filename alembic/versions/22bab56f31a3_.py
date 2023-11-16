"""empty message

Revision ID: 22bab56f31a3
Revises: 11075bc00836
Create Date: 2023-11-16 16:24:03.646731

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "22bab56f31a3"
down_revision: Union[str, None] = "11075bc00836"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "maestro_pair_association",
        sa.Column("maestro_instance_id", sa.UUID(), nullable=False),
        sa.Column("pair_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["maestro_instance_id"],
            ["maestro_instances.id"],
        ),
        sa.ForeignKeyConstraint(
            ["pair_id"],
            ["pairs.id"],
        ),
        sa.PrimaryKeyConstraint("maestro_instance_id", "pair_id"),
    )
    op.drop_constraint(
        "pairs_maestro_instance_id_fkey", "pairs", type_="foreignkey"
    )
    op.drop_column("pairs", "maestro_instance_id")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "pairs",
        sa.Column(
            "maestro_instance_id",
            sa.UUID(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "pairs_maestro_instance_id_fkey",
        "pairs",
        "maestro_instances",
        ["maestro_instance_id"],
        ["id"],
    )
    op.drop_table("maestro_pair_association")
    # ### end Alembic commands ###
