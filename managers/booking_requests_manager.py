from models import db, BookingRequest, booking_artists, Artist
from services.calculate_price import calculate_price
from flask import current_app
from datetime import date, time, timedelta

# Zulässige Statuswerte für Buchungsanfragen
ALLOWED_STATUSES = ["angefragt", "angeboten", "akzeptiert", "abgelehnt", "storniert"]

# Zulässige Event-Typen für Buchungsanfragen
ALLOWED_EVENT_TYPES = ['Private Feier', 'Firmenfeier', 'Incentive', 'Streetshow']


class BookingRequestManager:
    """
    Verwaltet Buchungsanfragen: Anlage, Abruf, Angebote und Statuswechsel.
    """

    def __init__(self):
        """Initialisiert den BookingRequestManager mit der Datenbanksitzung."""
        self.db = db

    def get_all_requests(self):
        """Gibt alle Buchungsanfragen zurück."""
        return BookingRequest.query.all()

    def get_request(self, request_id):
        """Gibt eine Buchungsanfrage anhand ihrer ID zurück oder None."""
        return BookingRequest.query.get(request_id)

    def create_request(
        self,
        client_name,
        client_email,
        event_date,
        duration_minutes,
        event_type,
        show_type,
        show_discipline,
        team_size,
        number_of_guests,
        event_address,
        is_indoor,
        special_requests,
        needs_light,
        needs_sound,
        artists,
        event_time="18:00",
        distance_km=0.0,
        newsletter_opt_in=False
    ):
        """Erstellt eine neue Buchungsanfrage und verknüpft sie mit Artists."""
        current_app.logger.info(f"create_request called with client={client_name}, disciplines={show_discipline}, artists={[getattr(a, 'id', a) for a in artists]}")

        # Datum und Zeit konvertieren
        if isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)
        if isinstance(event_time, str):
            event_time = time.fromisoformat(event_time)

        # Event-Type validieren
        if isinstance(event_type, str):
            matched = next(
                (e for e in ALLOWED_EVENT_TYPES if e.lower() == event_type.strip().lower()),
                None
            )
            if matched:
                event_type = matched
            else:
                raise ValueError(
                    f"Invalid event_type: {event_type}. Allowed: {ALLOWED_EVENT_TYPES}"
                )

        req = BookingRequest(
            client_name=client_name,
            client_email=client_email,
            event_date=event_date,
            event_time=event_time,
            duration_minutes=duration_minutes,
            event_type=event_type,
            show_type=show_type,
            show_discipline=",".join(show_discipline) if isinstance(show_discipline, list) else show_discipline,
            team_size=team_size,
            number_of_guests=number_of_guests,
            event_address=event_address,
            is_indoor=is_indoor,
            special_requests=special_requests,
            needs_light=needs_light,
            needs_sound=needs_sound,
            distance_km=distance_km,
            newsletter_opt_in=newsletter_opt_in
        )
        # Verknüpfung mit Artists
        for artist in artists:
            req.artists.append(artist)

        self.db.session.add(req)
        self.db.session.commit()
        return req

    def set_offer(self, request_id, artist_id, price_offered):
        """Speichert ein Angebot und aktualisiert den Status bei Solo oder nach vollständigen Angeboten."""
        current_app.logger.info(f"set_offer called for request_id={request_id}, artist_id={artist_id}, price_offered={price_offered}")
        # Angebot in Assoziationstabelle speichern
        self.db.session.execute(
            booking_artists.update()
            .where(booking_artists.c.booking_id == request_id)
            .where(booking_artists.c.artist_id == artist_id)
            .values(requested_gage=price_offered)
        )
        # Alle abgegebenen Gagen abrufen
        rows = self.db.session.execute(
            booking_artists.select()
            .with_only_columns(booking_artists.c.requested_gage)
            .where(booking_artists.c.booking_id == request_id)
        ).fetchall()
        gages = [r[0] for r in rows]

        req = self.get_request(request_id)
        # Solo-Booking oder alle Artists haben geboten
        if int(req.team_size) == 1 or all(g is not None for g in gages):
            raw = price_offered if int(req.team_size) == 1 else sum(g for g in gages if g is not None)
            req.status = "angeboten"
            # Finalpreis berechnen (inklusive Agenturgebühr, Technik etc.)
            min_p, _ = calculate_price(
                base_min=raw,
                base_max=raw,
                distance_km=req.distance_km,
                fee_pct=float(current_app.config.get("AGENCY_FEE_PERCENT", 20)),
                newsletter=req.newsletter_opt_in,
                event_type=None,
                num_guests=req.number_of_guests,
                is_weekend=req.event_date.weekday() >= 5,
                is_indoor=req.is_indoor,
                needs_light=req.needs_light,
                needs_sound=req.needs_sound,
                show_discipline=req.show_discipline,
                team_size=req.team_size,
                duration=req.duration_minutes,
                event_address=req.event_address
            )
            req.price_offered = min_p
            self.db.session.commit()

        return req

    def change_status(self, request_id, status):
        """Ändert den Status einer Buchungsanfrage, sofern der neue Status zulässig ist."""
        req = self.get_request(request_id)
        allowed = ALLOWED_STATUSES
        if req and status in allowed:
            req.status = status
            self.db.session.commit()
        return req

    def get_all_offers(self):
        """
        Gibt alle Buchungsanfragen zurück, die bereits ein Angebot erhalten haben.
        """
        return BookingRequest.query.filter(BookingRequest.price_offered.isnot(None)).all()

    def get_requests_for_artist_with_recommendation(self, artist_id):
        """
        Gibt zukünftige Buchungsanfragen zurück, die für den angegebenen Artist empfohlen werden,
        inklusive einer empfohlenen Preis-Spanne auf Basis von Artist-Parametern.
        """
        current_app.logger.info(f"get_requests_for_artist_with_recommendation called for artist_id={artist_id}")
        try:
            aid = int(artist_id)
        except (TypeError, ValueError):
            return []

        artist = Artist.query.get(aid)
        if not artist:
            current_app.logger.warning(f"No artist found with id={aid}")
            return []

        all_requests = self.get_all_requests()
        current_app.logger.info(f"Total requests in system: {len(all_requests)}")

        # Filtert Anfragen, in denen der Artist mitgewirkt hat
        relevant = [
            r for r in all_requests
            if any(a.id == aid for a in r.artists)
        ]
        current_app.logger.info(f"Relevant requests for artist {aid}: {[r.id for r in relevant]}")

        result = []
        for r in relevant:
            # Berechnung der empfohlenen Gage ohne Agentur-Gebühren oder Extras
            rec_min, rec_max = calculate_price(
                base_min=artist.price_min,
                base_max=artist.price_max,
                distance_km=0,
                fee_pct=0,
                newsletter=False,
                event_type=r.event_type,
                num_guests=r.number_of_guests,
                is_weekend=r.event_date.weekday() >= 5,
                is_indoor=r.is_indoor,
                needs_light=False,
                needs_sound=False,
                show_discipline=r.show_discipline,
                team_size=1,
                duration=r.duration_minutes,
                event_address=r.event_address
            )
            current_app.logger.info(f"Calculated recommendation for request {r.id}: min={rec_min}, max={rec_max}")
            result.append({
                'id': r.id,
                'client_name': r.client_name,
                'client_email': r.client_email,
                'event_date': r.event_date.isoformat(),
                'event_time': r.event_time.isoformat() if r.event_time else None,
                'duration_minutes': r.duration_minutes,
                'event_type': r.event_type,
                'show_type': getattr(r, 'show_type', None),
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