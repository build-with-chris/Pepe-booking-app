from models import db, Artist, BookingRequest, Availability, Discipline
from datetime import date, time

ALLOWED_DISCIPLINES = [
    "Zauberer",
    "Cyr-Wheel",
    "Bodenakrobatik",
    "Luftakrobatik",
    "Partnerakrobatik",
    "Chinese Pole",
    "Hula Hoop",
    "Handstand",
    "Contemporary Dance",
    "Breakdance",
    "Teeterboard",
    "Jonglage",
    "Moderation",
    "Pantomime/Entertainment"
]

ALLOWED_EVENT_TYPES = ['Private Feier', 'Firmenfeier', 'Incentive', 'Streetshow']


class DataManager:
    def __init__(self):
        self.db = db

    def get_or_create_discipline(self, name):
        from models import Discipline
        name = name.strip()
        for allowed in ALLOWED_DISCIPLINES:
            if allowed.lower() == name.lower():
                name = allowed  # normalize to official spelling
                break
        disc = Discipline.query.filter_by(name=name).first()
        if not disc:
            disc = Discipline(name=name)
            self.db.session.add(disc)
            self.db.session.commit()
        return disc

    # Artist methods
    def get_all_artists(self):
        return Artist.query.all()

    def get_artist(self, artist_id):
        return Artist.query.get(artist_id)
    
    # in datamanager.py, innerhalb class DataManager:
    def get_artist_by_email(self, email):
        return Artist.query.filter_by(email=email).first()

    def create_artist(self, name, email, password, disciplines,
                      phone_number=None, address=None,
                      price_min=1500, price_max=1900, is_admin=False):
        from datetime import timedelta
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
        for disc_name in disciplines:
            disc = self.get_or_create_discipline(disc_name)
            artist.disciplines.append(disc)
        self.db.session.add(artist)
        self.db.session.flush()  # so we have artist.id before commit

        # Add availabilities for next 365 days
        today = date.today()
        for i in range(365):
            day = today + timedelta(days=i)
            slot = Availability(artist_id=artist.id, date=day)
            self.db.session.add(slot)

        self.db.session.commit()
        return artist

    def get_artists_by_discipline(self, disciplines, event_date):
        """
        Returns Artists matching any given discipline AND available on event_date.
        """
        if isinstance(disciplines, str):
            disciplines = [disciplines]

        normalized = []
        for name in disciplines:
            name = name.strip()
            for allowed in ALLOWED_DISCIPLINES:
                if allowed.lower() == name.lower():
                    normalized.append(allowed)
                    break

        if isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)

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

    # BookingRequest methods
    def get_all_requests(self):
        return BookingRequest.query.all()

    def get_request(self, request_id):
        return BookingRequest.query.get(request_id)

    def create_request(self,
                       client_name, client_email,
                       event_date, duration_minutes,
                       event_type, show_discipline, team_size,
                       number_of_guests, event_address,
                       is_indoor, special_requests,
                       needs_light, needs_sound, 
                       artists, event_time="18:00",
                       distance_km=0.0, newsletter_opt_in=False):
        # event_date as date object or string 'YYYY-MM-DD'
        if isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)
        # event_time as string 'HH:MM'
        if isinstance(event_time, str):
            event_time = time.fromisoformat(event_time)

        # Normalize and validate event_type
        if isinstance(event_type, str):
            event_type_input = event_type.strip()
            matched = next((e for e in ALLOWED_EVENT_TYPES 
                            if e.lower() == event_type_input.lower()), None)
            if matched:
                event_type = matched
            else:
                raise ValueError(
                    f"Invalid event_type: {event_type}. "
                    f"Allowed: {ALLOWED_EVENT_TYPES}")
        if not isinstance(show_discipline, list):
            raise ValueError("show_discipline must be a list")
        for disc in show_discipline:
            if disc not in ALLOWED_DISCIPLINES:
                raise ValueError(f"Invalid discipline: {disc}")

        request = BookingRequest(
            client_name       = client_name,
            client_email      = client_email,
            event_date        = event_date,
            event_time        = event_time,
            duration_minutes  = duration_minutes,
            event_type        = event_type,
            show_discipline   = ", ".join(show_discipline),
            team_size         = team_size,
            number_of_guests  = number_of_guests,
            event_address     = event_address,
            is_indoor         = is_indoor,
            special_requests  = special_requests,
            needs_light       = needs_light,
            needs_sound       = needs_sound,
            distance_km       = distance_km,
            newsletter_opt_in = newsletter_opt_in
        )
        # associate artists
        for artist in artists:
            request.artists.append(artist)
        self.db.session.add(request)
        self.db.session.commit()
        return request

    def set_offer(self, request_id, price_offered):
        req = self.get_request(request_id)
        if req:
            req.price_offered = price_offered
            req.status = 'offered'
            self.db.session.commit()
        return req

    def change_status(self, request_id, status):
        req = self.get_request(request_id)
        if req and status in ['requested', 'offered', 'accepted', 'declined']:
            req.status = status
            self.db.session.commit()
        return req

    # Availability methods
    def get_availabilities(self, artist_id=None):
        query = Availability.query
        if artist_id:
            query = query.filter_by(artist_id=artist_id)
        return query.all()

    def add_availability(self, artist_id, date_obj):
        # date_obj: date or string
        if isinstance(date_obj, str):
            date_obj = date.fromisoformat(date_obj)
        existing = Availability.query.filter_by(artist_id=artist_id, date=date_obj).first()
        if existing:
            return existing  # Slot existiert schon, nichts tun
        slot = Availability(artist_id=artist_id, date=date_obj)
        self.db.session.add(slot)
        self.db.session.commit()
        return slot

    def remove_availability(self, availability_id):
        slot = Availability.query.get(availability_id)
        if slot:
            self.db.session.delete(slot)
            self.db.session.commit()
        return slot

    def delete_artist(self, artist_id):
            artist = Artist.query.get(artist_id)
            if artist:
                self.db.session.delete(artist)
                self.db.session.commit()
                return True
            return False
    
    def get_all_availabilities(self):
        """Gibt alle Availability-Einträge zurück, egal von welchem Artist."""
        return Availability.query.all()

    def get_all_offers(self):
        """
        Gibt alle BookingRequest-Einträge zurück, bei denen bereits ein Angebot 
        gesetzt wurde (price_offered != None).
        """
        return BookingRequest.query.filter(BookingRequest.price_offered.isnot(None)).all()