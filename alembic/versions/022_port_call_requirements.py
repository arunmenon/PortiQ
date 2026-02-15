"""Port call requirements for demand planning

Revision ID: 022
Revises: 021
Create Date: 2026-02-15

Creates: port_call_requirements
Enums: requirementcategory, requirementpriority, requirementstatus
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums
    requirementcategory = sa.Enum(
        "PROVISIONS", "TECHNICAL", "SAFETY", "DECK", "ENGINE",
        "CABIN", "SERVICES", "COMPLIANCE", "OTHER",
        name="requirementcategory",
    )
    requirementcategory.create(op.get_bind(), checkfirst=True)

    requirementpriority = sa.Enum(
        "LOW", "MEDIUM", "HIGH", "CRITICAL",
        name="requirementpriority",
    )
    requirementpriority.create(op.get_bind(), checkfirst=True)

    requirementstatus = sa.Enum(
        "DRAFT", "CONFIRMED", "RFQ_CREATED", "FULFILLED", "CANCELLED",
        name="requirementstatus",
    )
    requirementstatus.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "port_call_requirements",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("port_call_id", UUID(as_uuid=True), sa.ForeignKey("port_calls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("impa_code", sa.String(10), nullable=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_of_measure", sa.String(20), nullable=False),
        sa.Column("category", requirementcategory, nullable=False, server_default="OTHER"),
        sa.Column("priority", requirementpriority, nullable=False, server_default="MEDIUM"),
        sa.Column("status", requirementstatus, nullable=False, server_default="DRAFT"),
        sa.Column("rfq_id", UUID(as_uuid=True), sa.ForeignKey("rfqs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("specifications", JSONB, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_port_call_requirements_port_call", "port_call_requirements", ["port_call_id"])
    op.create_index("ix_port_call_requirements_org", "port_call_requirements", ["organization_id"])
    op.create_index("ix_port_call_requirements_status", "port_call_requirements", ["status"])
    op.create_index("ix_port_call_requirements_rfq", "port_call_requirements", ["rfq_id"])


def downgrade() -> None:
    op.drop_index("ix_port_call_requirements_rfq", table_name="port_call_requirements")
    op.drop_index("ix_port_call_requirements_status", table_name="port_call_requirements")
    op.drop_index("ix_port_call_requirements_org", table_name="port_call_requirements")
    op.drop_index("ix_port_call_requirements_port_call", table_name="port_call_requirements")
    op.drop_table("port_call_requirements")

    sa.Enum(name="requirementstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="requirementpriority").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="requirementcategory").drop(op.get_bind(), checkfirst=True)
