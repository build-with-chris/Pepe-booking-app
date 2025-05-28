from models import db, Artist, BookingRequest, Availability
from datetime import date, time

class DataManager:
    def __init__(self):
        self.db = db

    # Artist methods
    def get_all_artists(self):
        return Artist.query.all()

    def get_artist(self, artist_id):
        return Artist.query.get(artist_id)
    
    # in datamanager.py, innerhalb class DataManager:
    def get_artist_by_email(self, email):
        return Artist.query.filter_by(email=email).first()

    def create_artist(self, name, email, password, phone_number=None, address=None, price_min=1500, price_max=1900):
        artist = Artist(
            name=name,
            email=email,
            phone_number=phone_number,
            address=address,
            price_min=price_min,
            price_max=price_max
        )
        artist.set_password(password) 
        self.db.session.add(artist)
        self.db.session.commit()
        return artist

    # BookingRequest methods
    def get_all_requests(self):
        return BookingRequest.query.all()

    def get_request(self, request_id):
        return BookingRequest.query.get(request_id)

    def create_request(self,
                       client_name, client_email,
                       event_date, event_time,
                       duration_minutes,
                       event_type, show_type, team_size,
                       number_of_guests, event_address,
                       is_indoor, special_requests,
                       needs_light, needs_sound, needs_fog, artist_ids,
                       distance_km=0.0, newsletter_opt_in=False):
        # event_date as date object or string 'YYYY-MM-DD'
        if isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)
        # event_time as string 'HH:MM'
        if isinstance(event_time, str):
             event_time = time.fromisoformat(event_time)

        request = BookingRequest(
            client_name       = client_name,
            client_email      = client_email,
            event_date         = event_date,
            event_time         = event_time,
            duration_minutes   = duration_minutes,
            event_type         = event_type,
            show_type          = show_type,
            team_size          = team_size,
            number_of_guests   = number_of_guests,
            event_address      = event_address,
            is_indoor          = is_indoor,
            special_requests   = special_requests,
            needs_light        = needs_light,
            needs_sound        = needs_sound,
            needs_fog          = needs_fog,
            distance_km        = distance_km,
            newsletter_opt_in  = newsletter_opt_in
         )
   
        # associate artists
        for aid in artist_ids:
            artist = self.get_artist(aid)
            if artist:
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