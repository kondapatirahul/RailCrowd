"""Add passenger journey workspace and station facility records.

Revision ID: d3a7c91e42f0
Revises: b911af253a01
"""
from alembic import op
import sqlalchemy as sa

revision = "d3a7c91e42f0"
down_revision = "b911af253a01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "journey_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("origin_code", sa.String(length=10), nullable=False),
        sa.Column("origin_name", sa.String(length=120), nullable=False),
        sa.Column("destination_code", sa.String(length=10), nullable=False),
        sa.Column("destination_name", sa.String(length=120), nullable=False),
        sa.Column("travel_date", sa.Date(), nullable=False),
        sa.Column("passenger_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="planned", nullable=False),
        sa.Column("selected_option", sa.String(length=40), nullable=False),
        sa.Column("preferences", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("transfer_count", sa.Integer(), nullable=False),
        sa.Column("estimated_fare_low", sa.Integer(), nullable=True),
        sa.Column("estimated_fare_high", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("status IN ('draft','planned','in_progress','completed','cancelled')", name=op.f("ck_journey_plans_valid_journey_plan_status")),
        sa.CheckConstraint("passenger_count BETWEEN 1 AND 12", name=op.f("ck_journey_plans_valid_journey_passenger_count")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journey_plans")),
    )
    op.create_index("ix_journey_plans_user_id", "journey_plans", ["user_id"])
    op.create_index("ix_journey_plans_user_date", "journey_plans", ["user_id", "travel_date"])
    op.create_index("ix_journey_plans_route_date", "journey_plans", ["origin_code", "destination_code", "travel_date"])

    op.create_table(
        "journey_legs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("leg_order", sa.Integer(), nullable=False),
        sa.Column("train_number", sa.String(length=10), nullable=False),
        sa.Column("train_name", sa.String(length=160), nullable=False),
        sa.Column("from_code", sa.String(length=10), nullable=False),
        sa.Column("from_name", sa.String(length=120), nullable=False),
        sa.Column("to_code", sa.String(length=10), nullable=False),
        sa.Column("to_name", sa.String(length=120), nullable=False),
        sa.Column("departure_time", sa.String(length=5), nullable=True),
        sa.Column("arrival_time", sa.String(length=5), nullable=True),
        sa.Column("departure_offset_days", sa.Integer(), nullable=False),
        sa.Column("arrival_offset_days", sa.Integer(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("distance_km", sa.Integer(), nullable=True),
        sa.Column("coach_preference", sa.String(length=40), nullable=True),
        sa.Column("crowd_snapshot", sa.JSON(), nullable=False),
        sa.Column("timetable_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("leg_order >= 0", name=op.f("ck_journey_legs_valid_journey_leg_order")),
        sa.CheckConstraint("duration_minutes >= 0", name=op.f("ck_journey_legs_valid_journey_leg_duration")),
        sa.ForeignKeyConstraint(["plan_id"], ["journey_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journey_legs")),
        sa.UniqueConstraint("plan_id", "leg_order", name="uq_journey_leg_order"),
    )
    op.create_index("ix_journey_legs_plan_id", "journey_legs", ["plan_id"])
    op.create_index("ix_journey_legs_train_date", "journey_legs", ["train_number", "created_at"])

    op.create_table(
        "journey_checkpoints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("checkpoint_type", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("station_code", sa.String(length=10), nullable=True),
        sa.Column("is_completed", sa.Boolean(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("checkpoint_type IN ('before_departure','boarding','transfer','arrival','custom')", name=op.f("ck_journey_checkpoints_valid_journey_checkpoint_type")),
        sa.ForeignKeyConstraint(["plan_id"], ["journey_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journey_checkpoints")),
    )
    op.create_index("ix_journey_checkpoints_plan_id", "journey_checkpoints", ["plan_id"])
    op.create_index("ix_journey_checkpoints_plan_done", "journey_checkpoints", ["plan_id", "is_completed"])

    op.create_table(
        "journey_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("alert_type", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source_label", sa.String(length=80), nullable=False),
        sa.Column("station_code", sa.String(length=10), nullable=True),
        sa.Column("train_number", sa.String(length=10), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("severity IN ('info','watch','warning','critical')", name=op.f("ck_journey_alerts_valid_journey_alert_severity")),
        sa.ForeignKeyConstraint(["plan_id"], ["journey_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journey_alerts")),
    )
    op.create_index("ix_journey_alerts_plan_id", "journey_alerts", ["plan_id"])
    op.create_index("ix_journey_alerts_plan_active", "journey_alerts", ["plan_id", "is_active"])

    op.create_table(
        "journey_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("preferred_train_types", sa.JSON(), nullable=False),
        sa.Column("avoid_overnight", sa.Boolean(), nullable=False),
        sa.Column("max_transfers", sa.Integer(), nullable=False),
        sa.Column("min_transfer_minutes", sa.Integer(), nullable=False),
        sa.Column("accessibility_required", sa.Boolean(), nullable=False),
        sa.Column("prefer_lower_berth", sa.Boolean(), nullable=False),
        sa.Column("avoid_high_crowd", sa.Boolean(), nullable=False),
        sa.Column("preferred_coach", sa.String(length=40), nullable=True),
        sa.Column("notification_lead_minutes", sa.Integer(), nullable=False),
        sa.Column("extra", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journey_preferences")),
        sa.UniqueConstraint("user_id", name=op.f("uq_journey_preferences_user_id")),
    )

    op.create_table(
        "station_facilities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("station_code", sa.String(length=10), nullable=False),
        sa.Column("facility_type", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("location_hint", sa.String(length=240), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("accessibility_tags", sa.JSON(), nullable=False),
        sa.Column("reported_by_id", sa.Integer(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_visible", sa.Boolean(), nullable=False),
        sa.Column("moderated_by_id", sa.Integer(), nullable=True),
        sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("moderation_note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("facility_type IN ('restroom','drinking_water','waiting_room','cloak_room','food','medical','lift','escalator','wheelchair','parking','ticket_counter','wifi','charging','other')", name=op.f("ck_station_facilities_valid_station_facility_type")),
        sa.CheckConstraint("status IN ('available','limited','unavailable','unknown')", name=op.f("ck_station_facilities_valid_station_facility_status")),
        sa.ForeignKeyConstraint(["reported_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["moderated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_station_facilities")),
    )
    op.create_index("ix_station_facilities_station_code", "station_facilities", ["station_code"])
    op.create_index("ix_station_facilities_station_type", "station_facilities", ["station_code", "facility_type"])

    op.create_table(
        "station_facility_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("facility_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("is_still_available", sa.Boolean(), nullable=False),
        sa.Column("comment", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name=op.f("ck_station_facility_feedback_valid_facility_feedback_rating")),
        sa.ForeignKeyConstraint(["facility_id"], ["station_facilities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_station_facility_feedback")),
        sa.UniqueConstraint("facility_id", "user_id", name="uq_facility_feedback_user"),
    )
    op.create_index("ix_station_facility_feedback_facility_id", "station_facility_feedback", ["facility_id"])
    op.create_index("ix_station_facility_feedback_user_id", "station_facility_feedback", ["user_id"])

    op.create_table(
        "journey_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("overall_rating", sa.Integer(), nullable=False),
        sa.Column("punctuality_rating", sa.Integer(), nullable=True),
        sa.Column("crowd_accuracy_rating", sa.Integer(), nullable=True),
        sa.Column("transfer_rating", sa.Integer(), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("improvement_tags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("overall_rating BETWEEN 1 AND 5", name=op.f("ck_journey_feedback_valid_journey_feedback_rating")),
        sa.ForeignKeyConstraint(["plan_id"], ["journey_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journey_feedback")),
        sa.UniqueConstraint("plan_id", "user_id", name="uq_journey_feedback_user"),
    )
    op.create_index("ix_journey_feedback_plan_id", "journey_feedback", ["plan_id"])
    op.create_index("ix_journey_feedback_user_id", "journey_feedback", ["user_id"])

    op.create_table(
        "journey_shares",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("include_notes", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["journey_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journey_shares")),
        sa.UniqueConstraint("token_hash", name="uq_journey_share_token_hash"),
    )
    op.create_index("ix_journey_shares_plan_id", "journey_shares", ["plan_id"])

    op.create_table(
        "journey_search_presets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=80), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journey_search_presets")),
        sa.UniqueConstraint("user_id", "title", name="uq_journey_preset_user_title"),
    )
    op.create_index("ix_journey_search_presets_user_id", "journey_search_presets", ["user_id"])
    op.create_index("ix_journey_presets_user_updated", "journey_search_presets", ["user_id", "updated_at"])

    op.create_table(
        "journey_search_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("origin_code", sa.String(length=10), nullable=False),
        sa.Column("destination_code", sa.String(length=10), nullable=False),
        sa.Column("travel_date", sa.Date(), nullable=False),
        sa.Column("options_count", sa.Integer(), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=False),
        sa.Column("searched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journey_search_logs")),
    )
    op.create_index("ix_journey_search_logs_user_id", "journey_search_logs", ["user_id"])
    op.create_index("ix_journey_search_logs_user_time", "journey_search_logs", ["user_id", "searched_at"])
    op.create_index("ix_journey_search_logs_route", "journey_search_logs", ["origin_code", "destination_code"])


def downgrade():
    op.drop_index("ix_journey_search_logs_route", table_name="journey_search_logs")
    op.drop_index("ix_journey_search_logs_user_time", table_name="journey_search_logs")
    op.drop_index("ix_journey_search_logs_user_id", table_name="journey_search_logs")
    op.drop_table("journey_search_logs")
    op.drop_index("ix_journey_presets_user_updated", table_name="journey_search_presets")
    op.drop_index("ix_journey_search_presets_user_id", table_name="journey_search_presets")
    op.drop_table("journey_search_presets")
    op.drop_index("ix_journey_shares_plan_id", table_name="journey_shares")
    op.drop_table("journey_shares")
    op.drop_index("ix_journey_feedback_user_id", table_name="journey_feedback")
    op.drop_index("ix_journey_feedback_plan_id", table_name="journey_feedback")
    op.drop_table("journey_feedback")
    op.drop_index("ix_station_facility_feedback_user_id", table_name="station_facility_feedback")
    op.drop_index("ix_station_facility_feedback_facility_id", table_name="station_facility_feedback")
    op.drop_table("station_facility_feedback")
    op.drop_index("ix_station_facilities_station_type", table_name="station_facilities")
    op.drop_index("ix_station_facilities_station_code", table_name="station_facilities")
    op.drop_table("station_facilities")
    op.drop_table("journey_preferences")
    op.drop_index("ix_journey_alerts_plan_active", table_name="journey_alerts")
    op.drop_index("ix_journey_alerts_plan_id", table_name="journey_alerts")
    op.drop_table("journey_alerts")
    op.drop_index("ix_journey_checkpoints_plan_done", table_name="journey_checkpoints")
    op.drop_index("ix_journey_checkpoints_plan_id", table_name="journey_checkpoints")
    op.drop_table("journey_checkpoints")
    op.drop_index("ix_journey_legs_train_date", table_name="journey_legs")
    op.drop_index("ix_journey_legs_plan_id", table_name="journey_legs")
    op.drop_table("journey_legs")
    op.drop_index("ix_journey_plans_route_date", table_name="journey_plans")
    op.drop_index("ix_journey_plans_user_date", table_name="journey_plans")
    op.drop_index("ix_journey_plans_user_id", table_name="journey_plans")
    op.drop_table("journey_plans")
