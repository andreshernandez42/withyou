"""Baseline del esquema MVP With You.

Revision ID: 20261030_0001
Revises: None
Create Date: 2026-10-30

Esta migración establece la línea base del prototipo a partir del metadata
SQLAlchemy versionado. Las migraciones posteriores deben usar operaciones
Alembic incrementales/autogenerate, no create_all en producción.
"""
from alembic import op
from app.core.database import Base
from app import models  # noqa: F401

revision = '20261030_0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
