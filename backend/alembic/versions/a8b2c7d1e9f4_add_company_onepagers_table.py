"""add_company_onepagers_table

Revision ID: a8b2c7d1e9f4
Revises: f53264806529
Create Date: 2026-03-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "a8b2c7d1e9f4"
down_revision = "f53264806529"
branch_labels = None
depends_on = None


stance_enum = sa.Enum("green", "yellow", "red", name="stanceenum")


def upgrade() -> None:
    stance_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "company_onepagers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=True),
        sa.Column("generated_by", sa.String(), nullable=True),
        sa.Column("is_latest", sa.Boolean(), nullable=True),
        sa.Column("period_label", sa.String(), nullable=True),
        sa.Column("stance", stance_enum, nullable=True),
        sa.Column("stance_summary", sa.Text(), nullable=True),
        sa.Column("next_milestone", sa.Text(), nullable=True),
        sa.Column("metrics_table", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("performance_narrative", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("working_well", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("needs_improvement", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("value_creation", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("data_sources", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_edited_at", sa.DateTime(), nullable=True),
        sa.Column("edit_history", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_company_onepagers_company_id"), "company_onepagers", ["company_id"], unique=False)
    op.create_index(op.f("ix_company_onepagers_is_latest"), "company_onepagers", ["is_latest"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_company_onepagers_is_latest"), table_name="company_onepagers")
    op.drop_index(op.f("ix_company_onepagers_company_id"), table_name="company_onepagers")
    op.drop_table("company_onepagers")
    stance_enum.drop(op.get_bind(), checkfirst=True)
