from models import db, Artist
from models import Discipline, Availability, Artist
from datetime import date
from managers.discipline_manager import DisciplineManager
from datetime import date, timedelta
from managers.availability_manager import AvailabilityManager


class ArtistManager:
    """
    CRUD-Operationen für Artists und Anlage der Standard-Verfügbarkeit.
    """
    def __init__(self):
        """Initialisiert den ArtistManager mit der Datenbanksitzung."""
        self.db = db
        self.discipline_mgr = DisciplineManager()
        # Manager für Verfügbarkeiten
        self.availability_mgr = AvailabilityManager()

    def get_all_artists(self):
        """Gibt eine Liste aller Artists zurück."""
        return Artist.query.all()

    def get_artist(self, artist_id):
        """Gibt den Artist mit der angegebenen ID zurück oder None."""
        return Artist.query.get(artist_id)

    def get_artist_by_email(self, email):
        """Gibt den Artist mit gegebener E-Mail zurück oder None."""
        return Artist.query.filter_by(email=email).first()

    def create_artist(self, name, email, password, disciplines,
                      phone_number=None, address=None,
                      price_min=1500, price_max=1900, is_admin=False):
        """Legt einen neuen Artist mit Standardverfügbarkeit an."""
        artist = Artist(
            name=name,
            email=email,
            phone_number=phone_number,
            address=address,
            price_min=price_min,
            price_max=price_max,
            is_admin=is_admin,
        )
        artist.set_password(password)
        # Disziplinen zuordnen
        for disc_name in disciplines:
            disc = self.discipline_mgr.get_or_create_discipline(disc_name)
            artist.disciplines.append(disc)
        self.db.session.add(artist)
        self.db.session.flush()
        # Standard-Verfügbarkeit: 365 Tage ab heute über AvailabilityManager anlegen
        today = date.today()
        for i in range(365):
            day = today + timedelta(days=i)
            self.availability_mgr.add_availability(artist.id, day)
        self.db.session.commit()
        return artist


    def get_artists_by_discipline(self, disciplines, event_date):
        """
        Gibt Artists zurück, die am angegebenen Datum verfügbar sind und
        mindestens eine der gegebenen Disziplinen beherrschen.
        """
        if isinstance(disciplines, str):
            disciplines = [disciplines]

        # Normalisierung der Disziplinnamen
        normalized = []
        for name in disciplines:
            name = name.strip()
            for allowed in self.discipline_mgr.get_allowed_disciplines():
                if allowed.lower() == name.lower():
                    normalized.append(allowed)
                    break

        # Datum konvertieren
        if isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)

        # Query: join disciplines und availabilities
        return (
            Artist.query
            .join(Artist.disciplines)
            .join(Artist.availabilities)
            .filter(
                Discipline.name.in_(normalized),
                Availability.date == event_date
            )
            .all()
        )


    def delete_artist(self, artist_id):
        """
        Löscht einen Artist und alle zugehörigen Daten anhand der ID.
        """
        artist = self.get_artist(artist_id)
        if artist:
            self.db.session.delete(artist)
            self.db.session.commit()
            return True
        return False

