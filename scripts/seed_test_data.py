import sys
from pathlib import Path
# sicherstellen, dass das Projekt-Root im Import-Pfad ist
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import os
import json
import base64
import logging
from flask import Flask
from config import Config, normalize_db_url

# Modelle importieren
import models
try:
    from models import db, Artist, BookingRequest
except ImportError as e:
    raise RuntimeError(f"Import der Modelle fehlgeschlagen: {e}")

# Profile optional: prüfen, ob vorhanden
Profile = getattr(models, 'Profile', None)
if Profile is None:
    available = [n for n in dir(models) if not n.startswith('_')]
    logging.warning(f"Profile-Modell nicht gefunden. Verfügbare Exporte: {available}. Fallback auf direkte Artist-Verknüpfung.")

logging.basicConfig(level=logging.INFO)

# Supabase User ID extrahieren (ENV oder JWT)
def extract_sub_from_jwt(token: str) -> str:
    payload = token.split('.')[1]
    padded = payload + '=' * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(padded)).get('sub')

SUPABASE_USER_ID = os.getenv('SUPABASE_USER_ID')
if not SUPABASE_USER_ID:
    jwt = os.getenv('SUPABASE_JWT')
    if jwt:
        SUPABASE_USER_ID = extract_sub_from_jwt(jwt)
if not SUPABASE_USER_ID:
    raise RuntimeError('Keine SUPABASE_USER_ID oder SUPABASE_JWT gesetzt.')

logging.info(f'Using Supabase user id: {SUPABASE_USER_ID}')

# App & DB konfigurieren
app = Flask(__name__)
app.config.from_object(Config)
raw_db = os.getenv('DATABASE_URL', '')
if raw_db:
    app.config['SQLALCHEMY_DATABASE_URI'] = normalize_db_url(raw_db)

with app.app_context():
    db.init_app(app)
    db.create_all()

    # ----- Seed: Artist -----
    # Erzeuge Artist mit minimalen Pflichtfeldern (email darf nicht null sein)
    # password_hash erzeugen und ggf. kürzen auf 128 Zeichen
    password_hash = None
    if hasattr(models, 'generate_password_hash'):
        try:
            password_hash = models.generate_password_hash('changeme')
            if password_hash and len(password_hash) > 128:
                logging.warning('password_hash zu lang, kürze auf 128 Zeichen')
                password_hash = password_hash[:128]
        except Exception:
            logging.warning('Konnte password_hash nicht generieren')
    artist = Artist(
        id=1,
        name='Chris',
        email='chris@example.com',
        password_hash=password_hash,
        price_min=1500,
        price_max=1900,
        is_admin=False,
    )
    # supabase_user_id setzen, falls Feld vorhanden
    if hasattr(artist, 'supabase_user_id') or hasattr(Artist, 'supabase_user_id'):
        try:
            setattr(artist, 'supabase_user_id', SUPABASE_USER_ID)
        except Exception:
            logging.warning('Konnte supabase_user_id nicht setzen auf Artist; Feld existiert vielleicht anders.')
    db.session.merge(artist)
    db.session.flush()

    # ----- Seed: Profile (wenn vorhanden) -----
    if Profile is not None:
        profile = Profile(
            user_id=SUPABASE_USER_ID,
            backend_artist_id=str(artist.id),
            name='Chris',
            is_complete=True,
        )
        db.session.merge(profile)

    # ----- Seed: Booking Request -----
    br = BookingRequest(
        client_name='Test Kunde',
        client_email='test@kunde.de',
        event_type='Firmenfeier',
        show_type='Bühnen Show',
        show_discipline='Breakdance',
        team_size='1',
        number_of_guests=100,
        event_address='Musterstraße 1, Berlin',
        is_indoor=False,
        event_date='2025-09-15',
        event_time='18:00:00',
        duration_minutes=60,
        status='requested',
    )
    db.session.add(br)
    db.session.flush()  # br.id verfügbar machen

    # ----- Link Artist <-> BookingRequest -----
    if hasattr(models, 'booking_artists'):
        try:
            # Die association table benutzt offenbar 'booking_id' statt 'booking_request_id'
            db.session.execute(
                models.booking_artists.insert().values(
                    booking_id=br.id,
                    artist_id=artist.id,
                )
            )
        except Exception as e:
            logging.warning(f'Verknüpfung von Artist und BookingRequest fehlgeschlagen: {e}')

    try:
        db.session.commit()
        logging.info('✅ Seed erfolgreich: Artist, Profile (falls vorhanden), BookingRequest und Verknüpfung eingefügt.')
    except Exception:
        logging.exception('Fehler beim Seed. Rollback.')
        db.session.rollback()