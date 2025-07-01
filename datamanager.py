from models import db, Artist, BookingRequest, Availability, Discipline, booking_artists, AdminOffer
from services.calculate_price import calculate_price
from flask import current_app
from datetime import date, time, timedelta
import re

 # Zulässige Statuswerte für Buchungsanfragen
ALLOWED_STATUSES = ["angefragt", "angeboten", "akzeptiert", "abgelehnt", "storniert"]
 # Erlaubte Event-Typen für Buchungsanfragen
ALLOWED_EVENT_TYPES = ['Private Feier', 'Firmenfeier', 'Incentive', 'Streetshow']
 # Liste der erlaubten Disziplinen, die ein Artist ausüben kann
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

class DataManager:
    """
    Stellt Datenbank-Operationen für Artists, Buchungsanfragen und Verfügbarkeiten bereit.
    """
    def __init__(self):
        """Initialisiert den Datenmanager mit der Datenbanksitzung."""
        self.db = db

    # Methoden für Disziplin-Verwaltung
    def get_or_create_discipline(self, name):
        """Gibt eine vorhandene Disziplin anhand des Namens zurück oder legt sie an, falls sie nicht existiert."""
        name = name.strip()
        # Offizielle Schreibweise prüfen und normalisieren
        normalized = False
        for allowed in ALLOWED_DISCIPLINES:
            if allowed.lower() == name.lower():
                name = allowed
                normalized = True
                break

        # Validierung für unbekannte Namen (leer oder Sonderzeichen)
        if not normalized:
            if not name:
                raise ValueError("Disziplinname darf nicht leer sein")
            if not re.match(r'^[A-Za-z0-9 äöüÄÖÜß\/-]+$', name):
                raise ValueError(f"Ungültige Disziplin: {name}")
        disc = Discipline.query.filter_by(name=name).first()
        if not disc:
            disc = Discipline(name=name)
            self.db.session.add(disc)
            self.db.session.commit()
        return disc

    # Methoden für Artists
    def get_all_artists(self):
        """Gibt eine Liste aller Artists zurück."""
        return Artist.query.all()

    def get_artist(self, artist_id):
        """Gibt den Artist mit der angegebenen ID zurück oder None, wenn nicht gefunden."""
        return Artist.query.get(artist_id)
    
    def get_artist_by_email(self, email):
        """Gibt den Artist zur angegebenen E-Mail zurück oder None, falls nicht gefunden."""
        return Artist.query.filter_by(email=email).first()

    def create_artist(self, name, email, password, disciplines,
                      phone_number=None, address=None,
                      price_min=1500, price_max=1900, is_admin=False):
        """Legt einen neuen Artist mit den angegebenen Daten und Standard-Verfügbarkeit an."""

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
        self.db.session.flush()  

        # default: erstes Jahr verfügbar. 
        today = date.today()
        for i in range(365):
            day = today + timedelta(days=i)
            slot = Availability(artist_id=artist.id, date=day)
            self.db.session.add(slot)

        self.db.session.commit()
        return artist

    def get_artists_by_discipline(self, disciplines, event_date):
        """Gibt Artists zurück, die am angegebenen Datum verfügbar sind und mindestens eine der gegebenen Disziplinen beherrschen."""
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

    # Methoden für Buchungsanfragen
    def get_all_requests(self):
        """Gibt eine Liste aller Buchungsanfragen zurück."""
        return BookingRequest.query.all()

    def get_request(self, request_id):
        """Gibt die Buchungsanfrage mit der angegebenen ID zurück."""
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
        """Erstellt eine neue Buchungsanfrage und verknüpft sie mit passenden Artists."""
        # event_date: 'YYYY-MM-DD'
        if isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)
        # event_time as string 'HH:MM'
        if isinstance(event_time, str):
            event_time = time.fromisoformat(event_time)
        # validieren eventtyp
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
        # Verknüpfen mit entsprechenden artists
        for artist in artists:
            request.artists.append(artist)
        self.db.session.add(request)
        self.db.session.commit()
        return request

    def set_offer(self, request_id, artist_id, price_offered):
        """Speichert ein Angebot eines Artists für eine Buchungsanfrage und aktualisiert den Status."""
        # 1. Speichern der angegebenen Gage in der dazugehörigen Table
        self.db.session.execute(
            booking_artists.update()
                .where(booking_artists.c.booking_id == request_id)
                .where(booking_artists.c.artist_id == artist_id)
                .values(requested_gage=price_offered)
        )
        # 2. Check ob alle Artisten gage bereitgestellt haben (Solo vs. Duo)
        rows = self.db.session.execute(
            booking_artists.select().with_only_columns(booking_artists.c.requested_gage)
                .where(booking_artists.c.booking_id == request_id)
        ).fetchall()
        gages = [r[0] for r in rows]
        # Finalisiere sofort bei Solo-Booking (team_size '1') oder wenn alle Artists offeriert haben
        req = self.get_request(request_id)
        if int(req.team_size) == 1:
            # Solo-Booking: direktes Angebot der einzelnen Gage
            req.price_offered = price_offered
            req.status = "angeboten"
            # Berechnen des Kundenpreis (agency fee, tech, etc.)
            raw = req.price_offered
            min_p, _ = calculate_price(
                base_min       = raw,
                base_max       = raw,
                distance_km    = req.distance_km,
                fee_pct        = float(current_app.config.get("AGENCY_FEE_PERCENT", 20)),
                newsletter     = req.newsletter_opt_in,
                event_type     = None,
                num_guests     = 100,
                is_weekend     = False,
                is_indoor      = True,
                needs_light    = req.needs_light,
                needs_sound    = req.needs_sound,
                show_discipline= req.show_discipline,
                team_size      = req.team_size,
                duration       = req.duration_minutes,
                city           = None
            )
            req.price_offered = min_p
        elif all(g is not None for g in gages):
            # Duo+ : nur, wenn alle ihre Gage abgegeben haben
            total = sum(g for g in gages if g is not None)
            req.price_offered = total
            req.status = "angeboten"
                        # Recalculate final price including agency fee, tech, etc.
            raw = req.price_offered
            min_p, _ = calculate_price(
                base_min       = raw,
                base_max       = raw,
                distance_km    = req.distance_km,
                fee_pct        = float(current_app.config.get("AGENCY_FEE_PERCENT", 20)),
                newsletter     = req.newsletter_opt_in,
                event_type     = None,
                num_guests     = 100,
                is_weekend     = False,
                is_indoor      = True,
                needs_light    = req.needs_light,
                needs_sound    = req.needs_sound,
                show_discipline= req.show_discipline,
                team_size      = req.team_size,
                duration       = req.duration_minutes,
                city           = None
            )
            req.price_offered = min_p
        self.db.session.commit()
        return req

    def change_status(self, request_id, status):
        """Ändert den Status einer Buchungsanfrage, sofern der neue Status zulässig ist."""
        req = self.get_request(request_id)
        if req and status in ALLOWED_STATUSES:
            req.status = status
            self.db.session.commit()
        return req

    
    def delete_artist(self, artist_id):
        """Löscht einen Artist und alle zugehörigen Daten anhand der ID."""
        artist = Artist.query.get(artist_id)
        if artist:
            self.db.session.delete(artist)
            self.db.session.commit()
            return True
        return False
    

    def get_all_offers(self):
        """Gibt alle Buchungsanfragen zurück, die bereits Angebote erhalten haben."""
        return BookingRequest.query.filter(BookingRequest.price_offered.isnot(None)).all()

    def get_requests_for_artist_with_recommendation(self, artist_id):
        """Gibt zukünftige Buchungsanfragen zurück, die für den angegebenen Artist empfohlen werden."""
        try:
            artist_id = int(artist_id)
        except (TypeError, ValueError):
            return []

        artist = self.get_artist(artist_id)
        reqs = [r for r in self.get_all_requests() if any(a.id == artist_id for a in r.artists)]
        result = []
        for r in reqs:
            # Berechnung der empfohlenen Gage ohne agency fee und extras
            rec_min, rec_max = calculate_price(
                base_min       = artist.price_min,
                base_max       = artist.price_max,
                distance_km    = 0,
                fee_pct        = 0,
                newsletter     = False,
                event_type     = r.event_type,
                num_guests     = r.number_of_guests,
                is_weekend     = r.event_date.weekday() >= 5,
                is_indoor      = r.is_indoor,
                needs_light    = False,
                needs_sound    = False,
                show_discipline= r.show_discipline,
                team_size      = 1,
                duration       = r.duration_minutes,
                city           = None
            )
            # Response body für Artisten
            result.append({
                'id': r.id,
                'client_name': r.client_name,
                'client_email': r.client_email,
                'event_date': r.event_date.isoformat(),
                'event_time': r.event_time.isoformat() if r.event_time else None,
                'duration_minutes': r.duration_minutes,
                'event_type': r.event_type,
                'show_discipline': r.show_discipline,
                'team_size': r.team_size,
                'number_of_guests': r.number_of_guests,
                'event_address': r.event_address,
                'is_indoor': r.is_indoor,
                'special_requests': r.special_requests,
                'needs_light': r.needs_light,
                'needs_sound': r.needs_sound,
                'status': r.status,
                'artist_ids': [a.id for a in r.artists],
                'recommended_price_min': rec_min,
                'recommended_price_max': rec_max
            })
        return result
