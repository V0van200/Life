"""Initial Life schema. Schema snapshot is independent of application models."""
from alembic import op
import sqlalchemy as sa
revision="0001"
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("users",sa.Column("id",sa.String(36),primary_key=True),sa.Column("username",sa.String(100),nullable=False,unique=True),sa.Column("password",sa.Text,nullable=False))
    op.create_table("sessions",sa.Column("digest",sa.String(64),primary_key=True),sa.Column("owner",sa.String(36),sa.ForeignKey("users.id"),nullable=False),sa.Column("expires",sa.BigInteger,nullable=False))
    op.create_table("records",sa.Column("id",sa.String(36),primary_key=True),sa.Column("owner",sa.String(36),sa.ForeignKey("users.id"),nullable=False),sa.Column("kind",sa.String(50),nullable=False),sa.Column("title",sa.String(250),nullable=False),sa.Column("data",sa.Text,nullable=False),sa.Column("version",sa.Integer,nullable=False),sa.Column("created_at",sa.String(40),nullable=False),sa.Column("updated_at",sa.String(40),nullable=False))
    op.create_table("links",sa.Column("id",sa.String(36),primary_key=True),sa.Column("owner",sa.String(36),sa.ForeignKey("users.id"),nullable=False),sa.Column("source",sa.String(36),sa.ForeignKey("records.id"),nullable=False),sa.Column("target",sa.String(36),sa.ForeignKey("records.id"),nullable=False),sa.Column("relation",sa.String(80),nullable=False),sa.UniqueConstraint("source","target","relation"))
    op.create_table("accounts",sa.Column("id",sa.String(36),primary_key=True),sa.Column("owner",sa.String(36),sa.ForeignKey("users.id"),nullable=False),sa.Column("name",sa.String(100),nullable=False),sa.Column("currency",sa.String(3),nullable=False),sa.Column("opening_minor",sa.BigInteger,nullable=False))
    op.create_table("operations",sa.Column("id",sa.String(36),primary_key=True),sa.Column("owner",sa.String(36),sa.ForeignKey("users.id"),nullable=False),sa.Column("key",sa.String(100),nullable=False),sa.Column("kind",sa.String(20),nullable=False),sa.Column("account_id",sa.String(36),sa.ForeignKey("accounts.id"),nullable=False),sa.Column("target_id",sa.String(36),sa.ForeignKey("accounts.id")),sa.Column("amount_minor",sa.BigInteger,nullable=False),sa.Column("occurred_at",sa.String(40),nullable=False),sa.Column("title",sa.String(250),nullable=False),sa.Column("record_id",sa.String(36),sa.ForeignKey("records.id")),sa.UniqueConstraint("owner","key"),sa.CheckConstraint("amount_minor > 0"))
    op.create_table("obligations",sa.Column("id",sa.String(36),primary_key=True),sa.Column("owner",sa.String(36),sa.ForeignKey("users.id"),nullable=False),sa.Column("service_id",sa.String(36),sa.ForeignKey("records.id"),nullable=False),sa.Column("due",sa.String(10),nullable=False),sa.Column("amount_minor",sa.BigInteger,nullable=False),sa.Column("currency",sa.String(3),nullable=False),sa.Column("operation_id",sa.String(36),sa.ForeignKey("operations.id"),unique=True),sa.UniqueConstraint("service_id","due"),sa.CheckConstraint("amount_minor > 0"))
    op.create_table("audit",sa.Column("id",sa.String(36),primary_key=True),sa.Column("owner",sa.String(36),sa.ForeignKey("users.id"),nullable=False),sa.Column("entity_id",sa.String(36),nullable=False),sa.Column("action",sa.String(50),nullable=False),sa.Column("snapshot",sa.Text,nullable=False),sa.Column("at",sa.String(40),nullable=False))
    for table, columns in {"sessions":["owner"],"records":["owner","kind"],"links":["owner","source","target"],"accounts":["owner"],"operations":["owner","account_id","occurred_at"],"obligations":["owner","service_id","due"],"audit":["owner","entity_id"]}.items():
        for column in columns: op.create_index(f"ix_{table}_{column}",table,[column])

def downgrade():
    for table in ["audit","obligations","operations","accounts","links","records","sessions","users"]:
        op.drop_table(table)
