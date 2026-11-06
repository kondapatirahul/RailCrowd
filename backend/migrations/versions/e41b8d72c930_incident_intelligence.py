"""Add passenger incident intelligence, verification, watches, and advisories.

Revision ID: e41b8d72c930
Revises: d3a7c91e42f0
"""
from alembic import op
import sqlalchemy as sa

revision = "e41b8d72c930"
down_revision = "d3a7c91e42f0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rail_incidents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reporter_id", sa.Integer(), nullable=True),
        sa.Column("train_number", sa.String(10), nullable=True),
        sa.Column("train_name", sa.String(160), nullable=True),
        sa.Column("station_code", sa.String(10), nullable=True),
        sa.Column("station_name", sa.String(120), nullable=True),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("direction", sa.String(30), nullable=True),
        sa.Column("from_station", sa.String(10), nullable=True),
        sa.Column("to_station", sa.String(10), nullable=True),
        sa.Column("platform", sa.String(20), nullable=True),
        sa.Column("coach", sa.String(20), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expected_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verification_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contradiction_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impact_summary", sa.String(500), nullable=True),
        sa.Column("evidence_reference", sa.String(500), nullable=True),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("category IN ('delay','cancellation','platform_change','overcrowding','safety','cleanliness','facility','accessibility','security','track','other')", name="ck_rail_incidents_valid_incident_category"),
        sa.CheckConstraint("severity IN ('information','minor','major','critical')", name="ck_rail_incidents_valid_incident_severity"),
        sa.CheckConstraint("status IN ('pending','under_review','verified','monitoring','resolved','rejected','withdrawn','stale')", name="ck_rail_incidents_valid_incident_status"),
        sa.CheckConstraint("confidence BETWEEN 0 AND 100", name="ck_rail_incidents_valid_incident_confidence"),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_rail_incidents"),
    )
    op.create_index("ix_rail_incidents_reporter_id", "rail_incidents", ["reporter_id"])
    op.create_index("ix_rail_incidents_train_number", "rail_incidents", ["train_number"])
    op.create_index("ix_rail_incidents_station_code", "rail_incidents", ["station_code"])
    op.create_index("ix_rail_incidents_category", "rail_incidents", ["category"])
    op.create_index("ix_rail_incidents_status", "rail_incidents", ["status"])
    op.create_index("ix_incidents_status_created", "rail_incidents", ["status", "created_at"])
    op.create_index("ix_incidents_train_status", "rail_incidents", ["train_number", "status"])
    op.create_index("ix_incidents_station_status", "rail_incidents", ["station_code", "status"])
    op.create_index("ix_incidents_category_severity", "rail_incidents", ["category", "severity"])

    op.create_table(
        "incident_updates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("headline", sa.String(180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("old_status", sa.String(20), nullable=True),
        sa.Column("new_status", sa.String(20), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("extra", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["incident_id"], ["rail_incidents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_incident_updates"),
    )
    op.create_index("ix_incident_updates_incident_created", "incident_updates", ["incident_id", "created_at"])

    op.create_table(
        "incident_votes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("vote", sa.String(12), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("vote IN ('confirm','contradict')", name="ck_incident_votes_valid_incident_vote"),
        sa.ForeignKeyConstraint(["incident_id"], ["rail_incidents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_incident_votes"),
        sa.UniqueConstraint("incident_id", "user_id", name="uq_incident_vote_user"),
    )
    op.create_index("ix_incident_votes_incident_vote", "incident_votes", ["incident_id", "vote"])

    op.create_table(
        "incident_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("scope_key", sa.String(40), nullable=False),
        sa.Column("notify_updates", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_resolution", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("scope IN ('incident','train','station')", name="ck_incident_subscriptions_valid_incident_subscription_scope"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_incident_subscriptions"),
        sa.UniqueConstraint("user_id", "scope", "scope_key", name="uq_incident_subscription_scope"),
    )
    op.create_index("ix_incident_subscriptions_scope", "incident_subscriptions", ["scope", "scope_key"])

    op.create_table(
        "service_advisories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("affected_trains", sa.JSON(), nullable=False),
        sa.Column("affected_stations", sa.JSON(), nullable=False),
        sa.Column("alternative_guidance", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("severity IN ('info','caution','warning','critical')", name="ck_service_advisories_valid_advisory_severity"),
        sa.CheckConstraint("status IN ('draft','scheduled','published','expired','withdrawn')", name="ck_service_advisories_valid_advisory_status"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_service_advisories"),
    )
    op.create_index("ix_advisories_status_window", "service_advisories", ["status", "starts_at", "ends_at"])

    op.create_table(
        "incident_read_receipts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(20), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_incident_read_receipts"),
        sa.UniqueConstraint("user_id", "item_type", "item_id", name="uq_incident_receipt"),
    )


def downgrade():
    op.drop_table("incident_read_receipts")
    op.drop_index("ix_advisories_status_window", table_name="service_advisories")
    op.drop_table("service_advisories")
    op.drop_index("ix_incident_subscriptions_scope", table_name="incident_subscriptions")
    op.drop_table("incident_subscriptions")
    op.drop_index("ix_incident_votes_incident_vote", table_name="incident_votes")
    op.drop_table("incident_votes")
    op.drop_index("ix_incident_updates_incident_created", table_name="incident_updates")
    op.drop_table("incident_updates")
    for name in ("ix_incidents_category_severity", "ix_incidents_station_status", "ix_incidents_train_status", "ix_incidents_status_created", "ix_rail_incidents_status", "ix_rail_incidents_category", "ix_rail_incidents_station_code", "ix_rail_incidents_train_number", "ix_rail_incidents_reporter_id"):
        op.drop_index(name, table_name="rail_incidents")
    op.drop_table("rail_incidents")
