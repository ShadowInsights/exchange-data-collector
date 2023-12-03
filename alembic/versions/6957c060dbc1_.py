"""empty message

Revision ID: 6957c060dbc1
Revises: 4bd4ff963a6c
Create Date: 2023-12-03 12:30:43.170641

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6957c060dbc1"
down_revision: Union[str, None] = "4bd4ff963a6c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "order_book_anomalies",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        nullable=False,
        existing_server_default=sa.text(
            "'2023-11-18 18:57:12.422205'::timestamp without time zone"
        ),
    )
    op.drop_index(
        "ix_order_book_anomalies_updated_at", table_name="order_book_anomalies"
    )
    op.drop_index("ix_pairs_symbol", table_name="pairs")
    op.create_index(op.f("ix_pairs_symbol"), "pairs", ["symbol"], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_pairs_symbol"), table_name="pairs")
    op.create_index("ix_pairs_symbol", "pairs", ["symbol"], unique=False)
    op.create_index(
        "ix_order_book_anomalies_updated_at",
        "order_book_anomalies",
        ["updated_at"],
        unique=False,
    )
    op.alter_column(
        "order_book_anomalies",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        nullable=True,
        existing_server_default=sa.text(
            "'2023-11-18 18:57:12.422205'::timestamp without time zone"
        ),
    )
    # ### end Alembic commands ###
