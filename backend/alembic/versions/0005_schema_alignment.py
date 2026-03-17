"""schema alignment for routes, requests, users, and vehicles

Revision ID: 0005_schema_alignment
Revises: 0004_item_planned_activity
Create Date: 2026-03-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0005_schema_alignment"
down_revision = "0004_item_planned_activity"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    if not _has_table(inspector, table_name):
        return False
    return column_name in {c["name"] for c in inspector.get_columns(table_name)}


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    if not _has_table(inspector, table_name):
        return False
    return index_name in {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    created_vehicle_change_requests = False
    created_routes = False
    created_route_change_requests = False

    if _has_table(inspector, "vehicles"):
        if _has_column(inspector, "vehicles", "name"):
            try:
                op.alter_column("vehicles", "name", existing_type=sa.String(), nullable=True)
            except Exception:
                pass

        if not _has_column(inspector, "vehicles", "brand"):
            op.add_column("vehicles", sa.Column("brand", sa.String(), nullable=True))
            if _has_column(inspector, "vehicles", "name"):
                op.execute("UPDATE vehicles SET brand = name WHERE brand IS NULL")
            op.alter_column("vehicles", "brand", existing_type=sa.String(), nullable=False)

        if not _has_column(inspector, "vehicles", "identifier"):
            op.add_column("vehicles", sa.Column("identifier", sa.String(), nullable=True))

        if not _has_column(inspector, "vehicles", "consumption_l_per_100km"):
            op.add_column("vehicles", sa.Column("consumption_l_per_100km", sa.Float(), nullable=True))
            if _has_column(inspector, "vehicles", "consumption_l_per_km"):
                op.execute(
                    "UPDATE vehicles SET consumption_l_per_100km = consumption_l_per_km * 100.0 "
                    "WHERE consumption_l_per_100km IS NULL"
                )
            op.alter_column(
                "vehicles",
                "consumption_l_per_100km",
                existing_type=sa.Float(),
                nullable=False,
            )

        if not _has_column(inspector, "vehicles", "is_approved"):
            op.add_column(
                "vehicles",
                sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            )
            op.alter_column("vehicles", "is_approved", server_default=None)

        if not _has_column(inspector, "vehicles", "created_by"):
            op.add_column("vehicles", sa.Column("created_by", sa.Integer(), nullable=True))

    if _has_table(inspector, "users"):
        if not _has_column(inspector, "users", "email"):
            op.add_column("users", sa.Column("email", sa.String(), nullable=True))
        if not _has_column(inspector, "users", "rank"):
            op.add_column("users", sa.Column("rank", sa.String(), nullable=True))
        if not _has_column(inspector, "users", "position"):
            op.add_column("users", sa.Column("position", sa.String(), nullable=True))

    if "vehicle_change_requests" not in existing_tables:
        op.create_table(
            "vehicle_change_requests",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("vehicle_id", sa.Integer(), nullable=False),
            sa.Column("department_id", sa.Integer(), nullable=False),
            sa.Column("requested_by", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'PENDING'")),
            sa.Column("brand", sa.String(), nullable=True),
            sa.Column("identifier", sa.String(), nullable=True),
            sa.Column("fuel_type", sa.String(), nullable=True),
            sa.Column("consumption_l_per_100km", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("decided_at", sa.DateTime(), nullable=True),
            sa.Column("decided_by", sa.Integer(), nullable=True),
        )
        created_vehicle_change_requests = True

    if created_vehicle_change_requests or _has_index(inspector, "vehicle_change_requests", "ix_vcr_vehicle_id") is False:
        op.create_index("ix_vcr_vehicle_id", "vehicle_change_requests", ["vehicle_id"])
    if created_vehicle_change_requests or _has_index(inspector, "vehicle_change_requests", "ix_vcr_department_id") is False:
        op.create_index("ix_vcr_department_id", "vehicle_change_requests", ["department_id"])

    if "routes" not in existing_tables:
        op.create_table(
            "routes",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("department_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("points_json", sa.Text(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("distance_km", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("created_by", sa.Integer(), nullable=True),
        )
        created_routes = True

    if created_routes or _has_index(inspector, "routes", "ix_routes_department_id") is False:
        op.create_index("ix_routes_department_id", "routes", ["department_id"])

    if "route_change_requests" not in existing_tables:
        op.create_table(
            "route_change_requests",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("route_id", sa.Integer(), nullable=False),
            sa.Column("department_id", sa.Integer(), nullable=False),
            sa.Column("requested_by", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'PENDING'")),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("points_json", sa.Text(), nullable=True),
            sa.Column("distance_km", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("decided_at", sa.DateTime(), nullable=True),
            sa.Column("decided_by", sa.Integer(), nullable=True),
        )
        created_route_change_requests = True

    if created_route_change_requests or _has_index(inspector, "route_change_requests", "ix_rcr_route_id") is False:
        op.create_index("ix_rcr_route_id", "route_change_requests", ["route_id"])
    if created_route_change_requests or _has_index(inspector, "route_change_requests", "ix_rcr_department_id") is False:
        op.create_index("ix_rcr_department_id", "route_change_requests", ["department_id"])

    if _has_table(inspector, "requests"):
        if not _has_column(inspector, "requests", "route_id"):
            op.add_column("requests", sa.Column("route_id", sa.Integer(), nullable=True))
        if not _has_column(inspector, "requests", "route_is_manual"):
            op.add_column(
                "requests",
                sa.Column("route_is_manual", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            )
            op.alter_column("requests", "route_is_manual", server_default=None)
        if not _has_column(inspector, "requests", "persons_involved_count"):
            op.add_column(
                "requests",
                sa.Column(
                    "persons_involved_count",
                    sa.Integer(),
                    nullable=False,
                    server_default=sa.text("0"),
                ),
            )
            op.alter_column("requests", "persons_involved_count", server_default=None)
        if not _has_column(inspector, "requests", "training_days_count"):
            op.add_column(
                "requests",
                sa.Column(
                    "training_days_count",
                    sa.Integer(),
                    nullable=False,
                    server_default=sa.text("0"),
                ),
            )
            op.alter_column("requests", "training_days_count", server_default=None)

    if not _has_table(inspector, "planned_activities"):
        op.create_table(
            "planned_activities",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    if not _has_table(inspector, "request_planned_activities"):
        op.create_table(
            "request_planned_activities",
            sa.Column("request_id", sa.Integer(), nullable=False),
            sa.Column("planned_activity_id", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("request_id", "planned_activity_id"),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "request_planned_activities"):
        op.drop_table("request_planned_activities")
    if _has_table(inspector, "planned_activities"):
        op.drop_table("planned_activities")
    if _has_table(inspector, "route_change_requests"):
        op.drop_index("ix_rcr_department_id", table_name="route_change_requests")
        op.drop_index("ix_rcr_route_id", table_name="route_change_requests")
        op.drop_table("route_change_requests")
    if _has_table(inspector, "routes"):
        op.drop_index("ix_routes_department_id", table_name="routes")
        op.drop_table("routes")
    if _has_table(inspector, "vehicle_change_requests"):
        op.drop_index("ix_vcr_department_id", table_name="vehicle_change_requests")
        op.drop_index("ix_vcr_vehicle_id", table_name="vehicle_change_requests")
        op.drop_table("vehicle_change_requests")
