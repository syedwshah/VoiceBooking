"""booking and workflow entities

Revision ID: 20250214_02
Revises: 20250214_01
Create Date: 2025-09-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20250214_02"
down_revision = "20250214_01"
branch_labels = None
depends_on = None


booking_status_enum = postgresql.ENUM(
    "DRAFT",
    "PENDING",
    "CONFIRMED",
    "CANCELLED",
    name="booking_status",
    create_type=False,
)
payment_status_enum = postgresql.ENUM(
    "PENDING",
    "SUCCEEDED",
    "FAILED",
    "REFUNDED",
    name="payment_status",
    create_type=False,
)
payment_provider_enum = postgresql.ENUM(
    "MCP_SANDBOX",
    "MANUAL",
    name="payment_provider",
    create_type=False,
)


def upgrade() -> None:
    enums = {
        "booking_status": ("DRAFT", "PENDING", "CONFIRMED", "CANCELLED"),
        "payment_status": ("PENDING", "SUCCEEDED", "FAILED", "REFUNDED"),
        "payment_provider": ("MCP_SANDBOX", "MANUAL"),
    }

    for enum_name, values in enums.items():
        value_list = ", ".join(f"'{value}'" for value in values)
        statement = (
            "DO $$ BEGIN "
            f"IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum_name}') THEN "
            f"CREATE TYPE \"{enum_name}\" AS ENUM ({value_list}); "
            "END IF; END $$;"
        )
        op.execute(sa.text(statement))

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("external_id", sa.String(length=64), unique=True, nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone_number", sa.String(length=32), nullable=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("venue_id", sa.String(length=64), sa.ForeignKey("venues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("room_id", sa.String(length=64), sa.ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", booking_status_enum, nullable=False, server_default="DRAFT"),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("attendee_count", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_bookings_session_id", "bookings", ["session_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", payment_provider_enum, nullable=False),
        sa.Column("status", payment_status_enum, nullable=False, server_default="PENDING"),
        sa.Column("amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=True),
        sa.Column("sandbox_reference", sa.String(length=128), nullable=True),
        sa.Column("extras", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "door_access_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("door_code", sa.String(length=32), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("issued_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.UniqueConstraint("booking_id", name="uq_door_event_booking"),
    )

    op.create_table(
        "survey_responses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("action_items", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "call_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("call_type", sa.String(length=32), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_call_logs_session_id", "call_logs", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_call_logs_session_id", table_name="call_logs")
    op.drop_table("call_logs")

    op.drop_table("survey_responses")

    op.drop_table("door_access_events")

    op.drop_table("payments")

    op.drop_index("ix_bookings_session_id", table_name="bookings")
    op.drop_table("bookings")

    op.drop_table("customers")

    for enum_name in ("payment_provider", "payment_status", "booking_status"):
        statement = (
            "DO $$ BEGIN "
            f"IF EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum_name}') THEN "
            f"DROP TYPE \"{enum_name}\"; "
            "END IF; END $$;"
        )
        op.execute(sa.text(statement))
