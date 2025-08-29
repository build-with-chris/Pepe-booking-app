import logging
from models import db, Availability, Artist
from datetime import timedelta, date as _date
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

# helper: inclusive date range generator
def _date_range_inclusive(start: _date, end: _date):
    cur = start
    while cur <= end:
        yield cur
        cur = cur + timedelta(days=1)

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
            slots = Availability.query.order_by(Availability.artist_id, Availability.date).all()
            # Serialize slots to include artist_id
            return [
                {
                    'id': slot.id,
                    'date': slot.date.isoformat(),
                    'artist_id': slot.artist_id,
                }
                for slot in slots
            ]
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

    def ensure_available_for_all_on(self, target, only_approved: bool = True):
        """
        Legt für alle (oder nur freigegebene) Artists einen Verfügbarkeits-Slot am gegebenen Datum an.
        `target` akzeptiert date-Objekt oder ISO-String. Idempotent – bestehende Einträge werden übersprungen.
        Rückgabe: {"created": n, "skipped": m}
        """
        if isinstance(target, str):
            try:
                target = _date.fromisoformat(target)
            except ValueError:
                logger.warning('Ungültiges Datum in ensure_available_for_all_on: %s', target)
                raise
        created = 0
        skipped = 0
        try:
            q = Artist.query
            # Falls es ein approval_status-Feld gibt, optional darauf filtern
            try:
                if only_approved and hasattr(Artist, 'approval_status'):
                    q = q.filter(Artist.approval_status == 'approved')
            except Exception:
                # falls Schema anders ist, kein Filter – wir fahren fort
                pass
            artists = q.all()

            # Existierende Slots an diesem Tag für alle Artists abfragen, um N+1 zu vermeiden
            existing = (
                Availability.query
                .filter(Availability.date == target)
                .with_entities(Availability.artist_id)
                .all()
            )
            existing_ids = {row[0] for row in existing}

            to_create = [
                Availability(artist_id=artist.id, date=target)
                for artist in artists
                if artist.id not in existing_ids
            ]

            if to_create:
                self.db.session.bulk_save_objects(to_create)
                self.db.session.commit()
                created = len(to_create)
            else:
                created = 0
            skipped = len(artists) - created
            return {"created": created, "skipped": skipped, "date": target.isoformat()}
        except Exception:
            self.db.session.rollback()
            logger.exception('Fehler in ensure_available_for_all_on für Datum %s', target)
            raise

    def ensure_today_available_for_all(self, only_approved: bool = True):
        """Cron-Helfer: setzt den heutigen Tag für alle (oder nur freigegebene) Artists auf verfügbar."""
        return self.ensure_available_for_all_on(_date.today(), only_approved=only_approved)

    def ensure_availability_range_for_artist(self, artist_id: int, start, end) -> dict:
        """
        Legt fehlende Verfügbarkeiten für einen Artist für den (inklusiven) Zeitraum an.
        `start`/`end` akzeptieren date-Objekte oder ISO-Strings. Idempotent.
        Rückgabe: {"added": int, "skipped": int}
        """
        # Normalisieren
        if isinstance(start, str):
            start = _date.fromisoformat(start)
        if isinstance(end, str):
            end = _date.fromisoformat(end)
        if end < start:
            start, end = end, start
        try:
            # existierende Slots im Bereich laden (nur Datum)
            existing = (
                Availability.query
                .filter(Availability.artist_id == artist_id)
                .filter(Availability.date >= start, Availability.date <= end)
                .with_entities(Availability.date)
                .all()
            )
            existing_dates = {row[0] for row in existing}

            to_create = [
                Availability(artist_id=artist_id, date=dt)
                for dt in _date_range_inclusive(start, end)
                if dt not in existing_dates
            ]
            added = 0
            if to_create:
                self.db.session.bulk_save_objects(to_create)
                self.db.session.commit()
                added = len(to_create)
            else:
                added = 0
            skipped = len(existing_dates)
            return {"added": added, "skipped": skipped}
        except Exception:
            self.db.session.rollback()
            logger.exception('Fehler bei ensure_availability_range_for_artist artist_id=%s', artist_id)
            raise

    def ensure_auto_availability_for_artist(self, artist_id: int, days_ahead: int = 365) -> dict:
        """
        Convenience: Füllt alle Tage von heute bis heute+days_ahead-1 für einen Artist (idempotent).
        """
        start = _date.today()
        end = start + timedelta(days=days_ahead - 1)
        return self.ensure_availability_range_for_artist(artist_id, start, end)

   