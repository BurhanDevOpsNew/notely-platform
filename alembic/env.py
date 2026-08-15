import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.db import Base

# Import mit Nebenwirkung: registriert die Tabelle notes in Base.metadata
from app.models import Note  # noqa: F401

# Alembics Config-Objekt: Zugriff auf die Werte aus alembic.ini
config = context.config

# Die DB-URL kommt aus der Umgebung, nicht aus alembic.ini: sie ist ein Geheimnis
# und je Umgebung verschieden (localhost / postgres / notely_test).
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL must be set to run migrations")
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

# Python-Logging gemäß der ini-Datei einrichten
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Vergleichsbasis für --autogenerate: das Schema, wie der Code es beschreibt
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Migrationen im Offline-Modus ausführen.

    Konfiguriert den Kontext nur mit einer URL, ohne Engine — es wird also kein
    DBAPI-Treiber gebraucht und keine Verbindung aufgebaut. Statt SQL auszuführen,
    gibt Alembic es aus. Praktisch, um einem DBA das SQL zur Prüfung zu geben:
    `alembic upgrade head --sql`.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Migrationen im Online-Modus ausführen.

    Baut eine Engine und verbindet sich wirklich mit der Datenbank. Das ist der
    Normalfall bei `alembic upgrade head`. NullPool, weil dieser Prozess einmal
    läuft und danach endet — ein Verbindungspool wäre nur Ballast.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()