from models import db, Availability
from datetime import date

class AvailabilityManager:
    """
    Verwaltet Verfügbarkeitstage von Artists.
    """

    def __init__(self):
        """Initialisiert den AvailabilityManager mit der Datenbanksitzung."""
        self.db = db

    def get_availabilities(self, artist_id=None):
        """Gibt Verfügbarkeits-Slots zurück, optional gefiltert nach Artist-ID."""
        query = Availability.query
        if artist_id is not None:
            query = query.filter_by(artist_id=artist_id)
        return query.all()

    def get_all_availabilities(self):
        """Gibt alle Verfügbarkeitstage aller Artists zurück."""
        return Availability.query.all()

    def add_availability(self, artist_id, date_obj):
        """Fügt einen Verfügbarkeitstag für einen Artist an einem bestimmten Datum hinzu."""
        # date_obj kann String oder date sein
        if isinstance(date_obj, str):
            date_obj = date.fromisoformat(date_obj)
        existing = Availability.query.filter_by(
            artist_id=artist_id, date=date_obj
        ).first()
        if existing:
            return existing
        slot = Availability(artist_id=artist_id, date=date_obj)
        self.db.session.add(slot)
        self.db.session.commit()
        return slot

    def remove_availability(self, availability_id):
        """Entfernt einen Verfügbarkeitstag anhand seiner ID."""
        slot = Availability.query.get(availability_id)
        if slot:
            self.db.session.delete(slot)
            self.db.session.commit()
        return slot