"""add passenger notifications and saved trains

Revision ID: b911af253a01
Revises: c38e1b47764e
"""
from alembic import op
import sqlalchemy as sa

revision = "b911af253a01"
down_revision = "c38e1b47764e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "saved_trains",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("train_number", sa.String(length=10), nullable=False),
        sa.Column("train_name", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_saved_trains")),
        sa.UniqueConstraint("user_id", "train_number", name="uq_saved_train_user_number"),
    )
    with op.batch_alter_table("saved_trains") as batch_op:
        batch_op.create_index("ix_saved_trains_train_number", ["train_number"], unique=False)
        batch_op.create_index("ix_saved_trains_user_id", ["user_id"], unique=False)

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("report_updates", sa.Boolean(), nullable=False),
        sa.Column("crowd_changes", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification_preferences")),
        sa.UniqueConstraint("user_id", name=op.f("uq_notification_preferences_user_id")),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("notification_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("target_url", sa.String(length=300), nullable=False),
        sa.Column("dedupe_key", sa.String(length=180), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
        sa.UniqueConstraint("user_id", "dedupe_key", name="uq_notification_user_dedupe"),
    )
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.create_index("ix_notifications_user_created", ["user_id", "created_at"], unique=False)
        batch_op.create_index("ix_notifications_user_id", ["user_id"], unique=False)
        batch_op.create_index("ix_notifications_user_read", ["user_id", "is_read"], unique=False)


def downgrade():
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.drop_index("ix_notifications_user_read")
        batch_op.drop_index("ix_notifications_user_id")
        batch_op.drop_index("ix_notifications_user_created")
    op.drop_table("notifications")
    op.drop_table("notification_preferences")
    with op.batch_alter_table("saved_trains") as batch_op:
        batch_op.drop_index("ix_saved_trains_user_id")
        batch_op.drop_index("ix_saved_trains_train_number")
    op.drop_table("saved_trains")
