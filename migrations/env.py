import os
import sys
import logging
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool
import sqlalchemy as sa

# Projektwurzel ins Python-Pfad einfügen, damit lokale Importe funktionieren
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Alembic-Konfiguration laden
config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

# Logger für env
logger = logging.getLogger('alembic.env')

# Datenbank-URL normalisieren (falls vorhanden), sonst auf SQLite zurückfallen
try:
    from config import normalize_db_url
except ImportError:
    logger.warning('Konnte normalize_db_url nicht importieren; benutze raw DATABASE_URL oder SQLite fallback')
    def normalize_db_url(u):
        return u

raw_db_url = os.getenv('DATABASE_URL', '')
if raw_db_url:
    try:
        db_url = normalize_db_url(raw_db_url)
    except Exception as e:
        logger.warning(f'Fehler beim Normalisieren der DB-URL: {e}, verwende raw_db_url')
        db_url = raw_db_url
else:
    db_url = 'sqlite:///pepe.db'
config.set_main_option('sqlalchemy.url', db_url)
logger.info(f'Using DB URL for migrations: {db_url}')

# Metadata aus den Modellen importieren
try:
    from models import db
    target_metadata = db.metadata
except ImportError:
    logger.error('Konnte models.db nicht importieren; Migrationen werden nicht funktionieren')
    target_metadata = None


def run_migrations_offline():
    url = config.get_main_option('sqlalchemy.url')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    if target_metadata is None:
        logger.error('Keine target_metadata verfügbar, Migration abgebrochen.')
        raise RuntimeError('target_metadata is None')
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()