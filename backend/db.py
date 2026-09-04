import os
from contextlib import contextmanager
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, String, Integer, Boolean, JSON, Text, ForeignKey, select, text, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
TZ = ZoneInfo('America/Sao_Paulo')
def now(): return datetime.now(TZ)
def today(): return now().date().isoformat()
url = os.getenv('DATABASE_URL', 'sqlite:///' + str(ROOT / 'data' / 'ponto.db'))
if url.startswith('postgres://'): url = url.replace('postgres://', 'postgresql+psycopg://', 1)
if url.startswith('postgresql://'): url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
if os.getenv('RENDER') and url.startswith('sqlite'): raise RuntimeError('Configure DATABASE_URL PostgreSQL no Render.')
(ROOT / 'data').mkdir(exist_ok=True)
def connection_args(database_url):
    # Supavisor em modo transação não conserva comandos preparados.
    return {'check_same_thread': False, 'timeout': 30} if database_url.startswith('sqlite') else {'prepare_threshold': None}

engine = create_engine(url, pool_pre_ping=True, hide_parameters=True, connect_args=connection_args(url))
if engine.dialect.name == 'sqlite':
    @event.listens_for(engine, 'connect')
    def sqlite_integrity(connection, record):
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA busy_timeout=30000')
class Base(DeclarativeBase): pass
class Person(Base):
    __tablename__ = 'people'
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
    __tablename__ = 'schedules'
    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey('people.id', ondelete='RESTRICT'), index=True)
    effective: Mapped[str] = mapped_column(String(10), index=True)
    specific: Mapped[bool] = mapped_column(Boolean, default=False)
    days: Mapped[dict] = mapped_column(JSON)
class Day(Base):
    __tablename__ = 'days'
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey('people.id', ondelete='RESTRICT'), index=True)
    date: Mapped[str] = mapped_column(String(10), index=True)
    periods: Mapped[list] = mapped_column(JSON)
    punches: Mapped[list] = mapped_column(JSON, default=list)
    absent: Mapped[bool] = mapped_column(Boolean, default=False)
    overtime: Mapped[str] = mapped_column(String(40), default='')
class Item(Base):
    __tablename__ = 'items'
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey('people.id', ondelete='RESTRICT'), index=True)
    date: Mapped[str] = mapped_column(String(10), default=today)
    status: Mapped[str] = mapped_column(String(40), default='Pendente')
    data: Mapped[dict] = mapped_column(JSON, default=dict)
class Setting(Base):
    __tablename__ = 'settings'
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
class Audit(Base):
    __tablename__ = 'audit'
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(160))
    action: Mapped[str] = mapped_column(String(100))
    target: Mapped[str] = mapped_column(String(100))
    before: Mapped[dict] = mapped_column(JSON)
    after: Mapped[dict] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(Text)

def init():
    Base.metadata.create_all(engine)
    if engine.dialect.name == 'postgresql':
        with engine.begin() as connection:
            for table in Base.metadata.sorted_tables:
                connection.execute(text(f'ALTER TABLE "{table.name}" ENABLE ROW LEVEL SECURITY'))
                for role in ('anon', 'authenticated'):
                    if connection.scalar(text('SELECT 1 FROM pg_roles WHERE rolname=:role'), {'role':role}):
                        connection.execute(text(f'REVOKE ALL ON "{table.name}" FROM {role}'))
    with Session(engine) as db:
        if not db.get(Setting, 'mutex'):
            db.add(Setting(key='mutex', data={}))
            db.commit()

@contextmanager
def reading():
    with Session(engine, expire_on_commit=False) as db:
        yield db

@contextmanager
def transaction():
    with Session(engine, expire_on_commit=False) as db:
        try:
            # Serializar as alterações também entre processos.
            if engine.dialect.name == 'sqlite': db.execute(text('BEGIN IMMEDIATE'))
            else: db.execute(select(Setting).where(Setting.key == 'mutex').with_for_update()).scalar_one()
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise

def audit(db, actor, action, target, before=None, after=None, reason=''):
    db.add(Audit(at=now().isoformat(), actor=actor.name, action=action, target=str(target), before=before or {}, after=after or {}, reason=reason))
