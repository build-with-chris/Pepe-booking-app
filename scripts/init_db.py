import os, sys
# sicherstellen, dass das Projekt-Root im Module Search Path ist, damit `import config` funktioniert
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import os
import logging
from flask import Flask
from config import Config, normalize_db_url
from models import db

logging.basicConfig(level=logging.INFO)

# Versucht, die zentrale App-Factory zu verwenden, wenn sie existiert.
try:
    from app import create_app  # Falls dein app.py eine create_app factory exportiert
    app = create_app()
    logging.info('Verwende create_app() aus app.py')
except (ImportError, AttributeError):
    app = Flask(__name__)
    app.config.from_object(Config)
    logging.info('Verwende Standalone-Flask-App für DB-Init')
    # Falls RAW DATABASE_URL gesetzt ist, normalisieren (wird auch in Config passieren, aber sicherheitshalber)
    raw_db = os.getenv('DATABASE_URL', '')
    if raw_db:
        app.config['SQLALCHEMY_DATABASE_URI'] = normalize_db_url(raw_db)

with app.app_context():
    # Init und Schema-Erzeugung / Migration
    try:
        # Falls db noch nicht initialisiert wurde
        db.init_app(app)
        # Versuch Migrationen auszuwenden, wenn Flask-Migrate konfiguriert ist
        try:
            from flask_migrate import upgrade as migrate_upgrade

            logging.info('Versuche, Migrationen auszuführen (upgrade head)')
            migrate_upgrade()
        except Exception as e:  # fallback auf create_all
            logging.info('Migrationen fehlgeschlagen oder nicht vorhanden, benutze create_all(): %s', e)
            db.create_all()
        logging.info('✅ Schema initialisiert in der Postgres-Datenbank.')
    except Exception:
        logging.exception('Fehler beim Initialisieren des Schemas')
        raise

if __name__ == '__main__':
    # Ermöglicht direktes Ausführen als Script
    pass