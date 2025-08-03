import logging
from models import db, Availability, Artist
from datetime import date as _date
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

class AvailabilityManager:
    """
    Verwaltet Verfügbarkeitstage von Artists.
    """

    def __init__(self):
        """Initialisiert den AvailabilityManager mit der Datenbanksitzung."""
        self.db = db

    def get_availabilities(self, artist_id=None):
        """Gibt Verfügbarkeits-Slots zurück, optional gefiltert nach Artist-ID. Sortiert nach Datum aufsteigend."""
        try:
            query = Availability.query
            if artist_id is not None:
                query = query.filter_by(artist_id=artist_id)
            # explizite Sortierung sorgt für deterministische Reihenfolge
            return query.order_by(Availability.date).all()
        except Exception as e:
            logger.exception('Fehler beim Laden der Availabilities für artist_id=%s', artist_id)
            return []

    def get_all_availabilities(self):
        """Gibt alle Verfügbarkeitstage aller Artists zurück."""
        try:
            return Availability.query.order_by(Availability.artist_id, Availability.date).all()
        except Exception as e:
            logger.exception('Fehler beim Laden aller Availabilities')
            return []

    def add_availability(self, artist_id, date_obj):
        """Fügt einen Verfügbarkeitstag für einen Artist an einem bestimmten Datum hinzu. Idempotent (duplikate werden nicht erneut angelegt)."""
        if isinstance(date_obj, str):
            try:
                date_obj = _date.fromisoformat(date_obj)
            except ValueError:
                logger.warning('Ungültiges Datumsformat beim Hinzufügen der Availability: %s', date_obj)
                raise
        try:
            existing = Availability.query.filter_by(
                artist_id=artist_id, date=date_obj
            ).first()
            if existing:
                return existing
            slot = Availability(artist_id=artist_id, date=date_obj)
            self.db.session.add(slot)
            self.db.session.commit()
            return slot
        except IntegrityError:
            self.db.session.rollback()
            # noch einmal versuchen, evtl. wurde parallel angelegt
            existing = Availability.query.filter_by(artist_id=artist_id, date=date_obj).first()
            if existing:
                return existing
            logger.exception('IntegrityError beim Hinzufügen der Availability, aber kein bestehender Slot gefunden')
            raise
        except Exception:
            self.db.session.rollback()
            logger.exception('Fehler beim Hinzufügen der Availability für artist_id=%s date=%s', artist_id, date_obj)
            raise

    def remove_availability(self, availability_id):
        """Entfernt einen Verfügbarkeitstag anhand seiner ID. Gibt das gelöschte Slot-Objekt zurück oder None."""
        try:
            slot = Availability.query.get(availability_id)
            if slot:
                self.db.session.delete(slot)
                self.db.session.commit()
                return slot
            return None
        except Exception:
            self.db.session.rollback()
            logger.exception('Fehler beim Entfernen der Availability id=%s', availability_id)
            return None

    def replace_availabilities_for_artist(self, artist_id, new_dates):
        """Setzt die Verfügbarkeiten eines Artists auf genau die übergebenen new_dates (Liste von date oder ISO-Strings)."""
        # Normalisiere alle Daten zu date-Objekten
        normalized = set()
        for d in new_dates:
            if isinstance(d, str):
                try:
                    normalized.add(_date.fromisoformat(d))
                except ValueError:
                    logger.warning('Überspringe ungültiges Datum beim Ersetzen: %s', d)
            elif isinstance(d, _date):
                normalized.add(d)
        # bestehende Slots
        existing_slots = self.get_availabilities(artist_id)
        existing_dates = {s.date for s in existing_slots}

        to_add = normalized - existing_dates
        to_remove = existing_dates - normalized

        added = []
        removed = []
        for dt in to_add:
            try:
                slot = self.add_availability(artist_id, dt)
                added.append(slot)
            except Exception:
                logger.exception('Konnte Availability nicht hinzufügen: %s for artist %s', dt, artist_id)
        for dt in to_remove:
            slot = Availability.query.filter_by(artist_id=artist_id, date=dt).first()
            if slot:
                self.remove_availability(slot.id)
                removed.append(slot)
        return {
            'added': [s.id for s in added],
            'removed': [s.id for s in removed],
        }

    def get_availabilities_for_user(self, supabase_user_id):
        """Shortcut: Verfügbarkeiten für den eingeloggten Artist über Supabase-ID laden."""
        try:
            artist = Artist.query.filter_by(supabase_user_id=supabase_user_id).first()
            if not artist:
                logger.warning('Kein Artist für supabase_user_id=%s gefunden', supabase_user_id)
                return []
            return self.get_availabilities(artist.id)
        except Exception:
            logger.exception('Fehler beim Laden der Availabilities für supabase_user_id=%s', supabase_user_id)
            return []

    def replace_availabilities_for_user(self, supabase_user_id, new_dates):
        """Shortcut: Verfügbarkeiten für den eingeloggten Artist über Supabase-ID ersetzen."""
        try:
            artist = Artist.query.filter_by(supabase_user_id=supabase_user_id).first()
            if not artist:
                logger.warning('Kein Artist für supabase_user_id=%s gefunden', supabase_user_id)
                return {'added': [], 'removed': []}
            return self.replace_availabilities_for_artist(artist.id, new_dates)
        except Exception:
            logger.exception('Fehler beim Ersetzen der Availabilities für supabase_user_id=%s', supabase_user_id)
            return {'added': [], 'removed': []}