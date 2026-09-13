"""Baseline compatível com a versão 2.0; não remove registros existentes.

Snapshot independente dos modelos atuais, para migrações futuras não modificarem
esta revisão. Se as tabelas já existem, valida as colunas antes de registrar a versão.
"""

from alembic import op
from sqlalchemy import JSON, Boolean, ForeignKey, String, Text, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def today():
    return "1970-01-01"


class Base(DeclarativeBase):
    pass


class Person(Base):
    __tablename__ = "people"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    login: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(30))
    temporary: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    hired: Mapped[str] = mapped_column(String(10))
    terminated: Mapped[str | None] = mapped_column(String(10), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    session: Mapped[dict] = mapped_column(JSON, default=dict)


class Schedule(Base):
    __tablename__ = "schedules"
    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(
        ForeignKey("people.id", ondelete="RESTRICT"), index=True
    )
    effective: Mapped[str] = mapped_column(String(10), index=True)
    specific: Mapped[bool] = mapped_column(Boolean, default=False)
    days: Mapped[dict] = mapped_column(JSON)


class Day(Base):
    __tablename__ = "days"
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    person_id: Mapped[int] = mapped_column(
        ForeignKey("people.id", ondelete="RESTRICT"), index=True
    )
    date: Mapped[str] = mapped_column(String(10), index=True)
    periods: Mapped[list] = mapped_column(JSON)
    punches: Mapped[list] = mapped_column(JSON, default=list)
    absent: Mapped[bool] = mapped_column(Boolean, default=False)
    overtime: Mapped[str] = mapped_column(String(40), default="")


class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    person_id: Mapped[int] = mapped_column(
        ForeignKey("people.id", ondelete="RESTRICT"), index=True
    )
    date: Mapped[str] = mapped_column(String(10), default=today)
    status: Mapped[str] = mapped_column(String(40), default="Pendente")
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class Audit(Base):
    __tablename__ = "audit"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(160))
    action: Mapped[str] = mapped_column(String(100))
    target: Mapped[str] = mapped_column(String(100))
    before: Mapped[dict] = mapped_column(JSON)
    after: Mapped[dict] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(Text)


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = set(inspector.get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name in existing:
            actual = {column["name"] for column in inspector.get_columns(table.name)}
            missing = set(table.columns.keys()) - actual
            if missing:
                raise RuntimeError(
                    f"Tabela {table.name} incompatível; faltam colunas: {sorted(missing)}"
                )
    Base.metadata.create_all(bind, checkfirst=True)


def downgrade():
    raise RuntimeError(
        "Downgrade destrutivo desabilitado. Restaure um backup validado."
    )
