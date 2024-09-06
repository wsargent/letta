"""add blocks_agents to the mix

Revision ID: 4e6d79e6f021
Revises: cef7770889d4
Create Date: 2024-08-12 18:30:45.782239

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4e6d79e6f021"
down_revision: Union[str, None] = "cef7770889d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "blocks_agents",
        sa.Column("_agent_id", sa.UUID(), nullable=False),
        sa.Column("_block_id", sa.UUID(), nullable=False),
        sa.Column("_block_label", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["_agent_id"],
            ["agent._id"],
        ),
        sa.ForeignKeyConstraint(
            ["_block_id", "_block_label"],
            ["block._id", "block.label"],
        ),
        sa.PrimaryKeyConstraint("_agent_id", "_block_id", "_block_label"),
        sa.UniqueConstraint("_agent_id", "_block_label", name="unique_label_per_agent"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("blocks_agents")
    # ### end Alembic commands ###
