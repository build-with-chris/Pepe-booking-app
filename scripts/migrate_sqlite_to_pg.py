import os
import logging
from sqlalchemy import create_engine, MetaData, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def normalize_db_url(raw: str) -> str:
    if raw.startswith("postgres://"):
        return raw.replace("postgres://", "postgresql+psycopg://", 1)
    if raw.startswith("postgresql://") and not raw.startswith("postgresql+psycopg://"):
        return raw.replace("postgresql://", "postgresql+psycopg://", 1)
    return raw

 # --- source and target URLs ---
raw_sqlite_path = os.getenv("SQLITE_PATH", "pepe.db")
# absoluter, aufgelöster Pfad (falls relativ angegeben)
SQLITE_PATH = os.path.abspath(raw_sqlite_path)
if not os.path.exists(SQLITE_PATH):
    logging.error("SQLite-Datei existiert nicht: %s", SQLITE_PATH)
    raise SystemExit(1)
if os.path.getsize(SQLITE_PATH) == 0:
    logging.error("SQLite-Datei ist leer: %s", SQLITE_PATH)
    raise SystemExit(1)
SQLITE_URL = f"sqlite:///{SQLITE_PATH}"
raw_pg = os.getenv("DATABASE_URL", "")
if not raw_pg:
    raise RuntimeError("DATABASE_URL environment variable is required for target Postgres")
PG_URL = normalize_db_url(raw_pg)

logging.info(f"SQLite source: {SQLITE_URL}")
logging.info(f"Postgres target: {PG_URL}")

source_engine: Engine = create_engine(SQLITE_URL)
target_engine: Engine = create_engine(PG_URL)

source_meta = MetaData()
source_meta.reflect(bind=source_engine)
target_meta = MetaData()
target_meta.reflect(bind=target_engine)

logging.info(f"Reflektierte Quell-Tabellen: {list(source_meta.tables.keys())}")
logging.info(f"Reflektierte Ziel-Tabellen: {list(target_meta.tables.keys())}")
if not source_meta.tables:
    logging.error("Keine Tabellen in der SQLite-Quelle entdeckt. Stelle sicher, dass pepe.db existiert und Daten enthält.")

preferred_order = [
    'disciplines',
    'artists',
    'booking_requests',
    'availabilities',
    'artist_disciplines',
    'booking_artists',
    'admin_offers',
]

ordered_tables = []
for name in preferred_order:
    if name in source_meta.tables:
        ordered_tables.append(source_meta.tables[name])
for t in source_meta.sorted_tables:
    if t not in ordered_tables:
        ordered_tables.append(t)

for table in ordered_tables:
    logging.info(f"--- Migrating table: {table.name} ---")
    if table.name not in target_meta.tables:
        logging.warning(f"Target does not have table {table.name}, skipping.")
        continue
    target_table = target_meta.tables[table.name]

    try:
        with source_engine.connect() as src_conn:
            result = src_conn.execute(select(table))
            rows = result.fetchall()
    except SQLAlchemyError as e:
        logging.error(f"Failed reading from source table {table.name}: {e}")
        continue

    if not rows:
        logging.info(f"No rows to migrate for {table.name}")
        continue

    with target_engine.begin() as dest_conn:
        for row in rows:
            data = dict(row._mapping)
            try:
                stmt = pg_insert(target_table).values(**data)
                pk_cols = [c.name for c in target_table.primary_key.columns]
                if pk_cols:
                    stmt = stmt.on_conflict_do_nothing(index_elements=pk_cols)
                dest_conn.execute(stmt)
            except Exception:
                try:
                    dest_conn.execute(target_table.insert().values(**data))
                except Exception as ex:
                    logging.warning(f"Insert failed for table {table.name} row {data}: {ex}")
        logging.info(f"Finished inserting {len(rows)} rows into {table.name}")

def adjust_sequence(conn, table_name: str, pk_column: str = 'id'):
    try:
        seq_sql = text(f"SELECT pg_get_serial_sequence(:table, :column)")
        result = conn.execute(seq_sql, {"table": table_name, "column": pk_column})
        seq = result.scalar()
        if not seq:
            logging.info(f"No sequence found for {table_name}.{pk_column}, skipping sequence adjustment.")
            return
        max_id_sql = text(f"SELECT MAX({pk_column}) FROM {table_name}")
        max_id = conn.execute(max_id_sql).scalar() or 0
        if max_id == 0:
            logging.info(f"Table {table_name} empty or max id is 0, skipping setval.")
            return
        setval_sql = text(f"SELECT setval(:seq, :newval, true)")
        conn.execute(setval_sql, {"seq": seq, "newval": max_id})
        logging.info(f"Sequence {seq} for {table_name} set to {max_id}")
    except Exception as e:
        logging.warning(f"Failed adjusting sequence for {table_name}: {e}")

with target_engine.connect() as conn:
    for tbl in ['artists', 'booking_requests', 'disciplines', 'availabilities', 'admin_offers']:
        if tbl in target_meta.tables:
            adjust_sequence(conn, tbl, 'id')

logging.info('✅ Migration complete.')