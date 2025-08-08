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
        # Angebot in Assoziationstabelle speichern und Status auf 'angeboten' setzen
        res = self.db.session.execute(
            booking_artists.update()
            .where(booking_artists.c.booking_id == request_id)
            .where(booking_artists.c.artist_id == artist_id)
            .values(requested_gage=price_offered, status='angeboten')
        )
        current_app.logger.debug(
            f"set_offer pivot update rowcount={res.rowcount} request_id={request_id} artist_id={artist_id} price_offered={price_offered}"
        )
        if res.rowcount == 0:
            # Falls die Verknüpfung fehlt, lege sie an
            self.db.session.execute(
                booking_artists.insert().values(
                    booking_id=request_id,
                    artist_id=artist_id,
                    requested_gage=price_offered,
                    status='angeboten'
                )
            )
            current_app.logger.debug("set_offer pivot insert performed for missing association")
        # Wichtig: Pivot-Update sofort festschreiben, damit nachfolgende Reads (z.B. Admin) die Gage sehen
        self.db.session.commit()
        # (Der Rest der bisherigen Logik zur Preisberechnung/Status kann nach Bedarf wieder ergänzt werden)
        return self.get_request(request_id)

    def set_artist_status(self, request_id: int, artist_id: int, status: str) -> bool:
        """Setzt den Status für genau EINEN Artist innerhalb einer Anfrage."""
        if status not in ALLOWED_STATUSES:
            return False
        res = self.db.session.execute(
            booking_artists.update()
            .where(booking_artists.c.booking_id == request_id)
            .where(booking_artists.c.artist_id == artist_id)
            .values(status=status)
        )
        self.db.session.commit()
        return res.rowcount > 0

    def set_artists_status(self, request_id: int, artist_ids: list[int], status: str) -> int:
        """Setzt den Status für eine Menge von Artists; gibt Anzahl aktualisierter Zeilen zurück."""
        if status not in ALLOWED_STATUSES or not artist_ids:
            return 0
        res = self.db.session.execute(
            booking_artists.update()
            .where(booking_artists.c.booking_id == request_id)
            .where(booking_artists.c.artist_id.in_(artist_ids))
            .values(status=status)
        )
        self.db.session.commit()
        return res.rowcount

    def set_all_artists_status(self, request_id: int, status: str) -> int:
        """Setzt den Status für ALLE Artists einer Anfrage; gibt Anzahl aktualisierter Zeilen zurück."""
        if status not in ALLOWED_STATUSES:
            return 0
        res = self.db.session.execute(
            booking_artists.update()
            .where(booking_artists.c.booking_id == request_id)
            .values(status=status)
        )
        self.db.session.commit()
        return res.rowcount

    def get_artist_statuses(self, request_id: int):
        """Liefert pro Artist den Status und die gesendete Gage für eine Anfrage zurück."""
        rows = self.db.session.execute(
            booking_artists.select()
            .with_only_columns(
                booking_artists.c.artist_id,
                booking_artists.c.status,
                booking_artists.c.requested_gage
            )
            .where(booking_artists.c.booking_id == request_id)
        ).fetchall()
        return [
            {'artist_id': r[0], 'status': r[1], 'requested_gage': r[2]} for r in rows
        ]

    def change_status(self, request_id, status):
        """Ändert den Status einer Buchungsanfrage, sofern der neue Status zulässig ist."""
        req = self.get_request(request_id)
        if not req or status not in ALLOWED_STATUSES:
            return None
        req.status = status
        self.db.session.commit()
        return req

    def get_all_offers(self):
        """
        Gibt alle Buchungsanfragen zurück, die bereits ein Angebot erhalten haben.
        """
        return BookingRequest.query.filter(BookingRequest.price_offered.isnot(None)).all()

    def get_requests_for_artist(self, artist_id):
        """Gibt Buchungsanfragen zurück, in denen der Artist beteiligt ist. (Debug: ohne Datumseinschränkung)"""
        try:
            aid = int(artist_id)
        except (TypeError, ValueError):
            current_app.logger.warning(f"Invalid artist_id passed to get_requests_for_artist: {artist_id}")
            return []

        query = (
            BookingRequest.query
            .join(booking_artists, booking_artists.c.booking_id == BookingRequest.id)
            .filter(booking_artists.c.artist_id == aid)
            .filter(BookingRequest.status.in_(ALLOWED_STATUSES))
        )
        results = query.all()
        current_app.logger.debug(f"get_requests_for_artist: artist_id={aid}, found {[r.id for r in results]}")
        if not results:
            # zusätzliche Diagnose: was ist in der Assoziationstabelle?
            assoc_rows = self.db.session.execute(
                booking_artists.select().where(booking_artists.c.artist_id == aid)
            ).fetchall()
            current_app.logger.debug(f"booking_artists rows for artist {aid}: {assoc_rows}")
            # nochmal alle verknüpften Requests ohne Statusfilter
            fallback = (
                BookingRequest.query
                .join(booking_artists, booking_artists.c.booking_id == BookingRequest.id)
                .filter(booking_artists.c.artist_id == aid)
                .all()
            )
            current_app.logger.debug(f"Fallback linked requests for artist {aid} (no status filter): {[r.id for r in fallback]}")
        return results

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

        relevant = self.get_requests_for_artist(aid)
        current_app.logger.info(f"Relevant requests for artist {aid}: {[r.id for r in relevant]}")

        result = []
        for r in relevant:
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
                'recommended_price_max': rec_max,
                # Neu: tatsächliches Angebot und Datum
                'artist_gage': getattr(r, 'artist_gage', None),
                'artist_offer_date': r.artist_offer_date.isoformat() if getattr(r, 'artist_offer_date', None) else None
            })
        return result
    
    def get_artist_offer(self, request_id, artist_id):
        """Gibt das vom Artist eingereichte Angebot (Pivot) für eine bestimmte Anfrage zurück."""
        # Verifizieren, dass die Anfrage existiert und der Artist zugeordnet ist
        req = self.get_request(request_id)
        if not req:
            return None
        if artist_id not in [a.id for a in req.artists]:
            return None
        # Aus der Assoziationstabelle lesen (Single Source of Truth)
        row = self.db.session.execute(
            booking_artists.select()
            .with_only_columns(
                booking_artists.c.requested_gage,
                booking_artists.c.status
            )
            .where(booking_artists.c.booking_id == request_id)
            .where(booking_artists.c.artist_id == artist_id)
        ).fetchone()
        if not row:
            return None
        # Response-Form an FE anpassen
        return {
            'price_offered': row[0],
            'status': row[1]
        }