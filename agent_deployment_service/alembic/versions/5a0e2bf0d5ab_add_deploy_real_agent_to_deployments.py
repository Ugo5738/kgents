"""add deploy_real_agent to deployments

Revision ID: 5a0e2bf0d5ab
Revises: 0258f662b012
Create Date: 2025-08-09 05:55:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "5a0e2bf0d5ab"
down_revision = "0258f662b012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add column with a server_default to backfill existing rows
    op.add_column(
        "deployments",
        sa.Column(
            "deploy_real_agent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("deployments", "deploy_real_agent")
