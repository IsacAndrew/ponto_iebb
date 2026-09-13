from sqlalchemy import MetaData, Table, inspect, text

from .db import Person, Setting

TABLES = (
    "audit",
    "days",
    "items",
    "schedules",
    "settings",
    "people",
    "registros_ponto",
    "usuarios",
)


def clear_system_data(db, actor):
    connection = db.connection()
    postgres = connection.dialect.name == "postgresql"
    schema = "public" if postgres else None
    existing = set(inspect(connection).get_table_names(schema=schema))
    names = [name for name in TABLES if name in existing]
    saved = {
        column.name: getattr(actor, column.name) for column in Person.__table__.columns
    }
    saved.update(role="Suporte", details={}, session={})
    db.expunge_all()
    if postgres:
        connection.execute(text("SET LOCAL lock_timeout = '5s'"))
        targets = ", ".join(f'ONLY public."{name}"' for name in names)
        connection.execute(text(f"TRUNCATE TABLE {targets} CONTINUE IDENTITY RESTRICT"))
    else:
        metadata = MetaData()
        for name in names:
            Table(name, metadata, autoload_with=connection)
        for table in reversed(metadata.sorted_tables):
            if table.name in names:
                connection.execute(table.delete())
    # Recriar o acesso e a trava dentro da mesma transação.
    connection.execute(Person.__table__.insert().values(**saved))
    connection.execute(Setting.__table__.insert().values(key="mutex", data={}))
    return db.get(Person, saved["id"])
