"""Repair missing station and train catalogue tables on upgraded databases.

Revision ID: f2a6c91d4e80
Revises: e41b8d72c930
"""
from alembic import op
import sqlalchemy as sa

revision = "f2a6c91d4e80"
down_revision = "e41b8d72c930"
branch_labels = None
depends_on = None


def _table_exists(name):
    return sa.inspect(op.get_bind()).has_table(name)


def _index_exists(name, table):
    return any(item["name"] == name for item in sa.inspect(op.get_bind()).get_indexes(table))


def upgrade():
    if not _table_exists("stations"):
        op.create_table(
            "stations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(10), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("city", sa.String(100), nullable=True),
            sa.Column("state", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
    if _table_exists("stations"):
        if not _index_exists("ix_stations_code", "stations"):
            op.create_index("ix_stations_code", "stations", ["code"], unique=True)
        if not _index_exists("ix_stations_name", "stations"):
            op.create_index("ix_stations_name", "stations", ["name"])
        if not _index_exists("ix_stations_city", "stations"):
            op.create_index("ix_stations_city", "stations", ["city"])

    if not _table_exists("trains"):
        op.create_table(
            "trains",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("number", sa.String(10), nullable=False),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("train_type", sa.String(60), nullable=True),
            sa.Column("source_station_id", sa.Integer(), nullable=False),
            sa.Column("destination_station_id", sa.Integer(), nullable=False),
            sa.Column("departure_time", sa.String(5), nullable=True),
            sa.Column("arrival_time", sa.String(5), nullable=True),
            sa.Column("running_days", sa.String(30), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["source_station_id"], ["stations.id"]),
            sa.ForeignKeyConstraint(["destination_station_id"], ["stations.id"]),
        )
    if _table_exists("trains"):
        if not _index_exists("ix_trains_number", "trains"):
            op.create_index("ix_trains_number", "trains", ["number"], unique=True)
        if not _index_exists("ix_trains_name", "trains"):
            op.create_index("ix_trains_name", "trains", ["name"])
        if not _index_exists("ix_trains_is_active", "trains"):
            op.create_index("ix_trains_is_active", "trains", ["is_active"])

    if not _table_exists("train_stops"):
        op.create_table(
            "train_stops",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("train_id", sa.Integer(), nullable=False),
            sa.Column("station_id", sa.Integer(), nullable=False),
            sa.Column("stop_order", sa.Integer(), nullable=False),
            sa.Column("arrival_time", sa.String(5), nullable=True),
            sa.Column("departure_time", sa.String(5), nullable=True),
            sa.Column("halt_minutes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["train_id"], ["trains.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["station_id"], ["stations.id"]),
            sa.UniqueConstraint("train_id", "stop_order", name="uq_train_stop_order"),
        )
    if _table_exists("train_stops"):
        if not _index_exists("ix_train_stops_train_id", "train_stops"):
            op.create_index("ix_train_stops_train_id", "train_stops", ["train_id"])
        if not _index_exists("ix_train_stops_station_id", "train_stops"):
            op.create_index("ix_train_stops_station_id", "train_stops", ["station_id"])


def downgrade():
    # This compatibility repair only creates missing catalogue tables. Keep
    # them on downgrade because earlier application revisions depend on them.
    pass
