from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin 

db = SQLAlchemy()

# Association table for many-to-many between Artist and BookingRequest
booking_artists = db.Table(
    'booking_artists',
    db.Column('booking_id', db.Integer, db.ForeignKey('booking_requests.id'), primary_key=True),
    db.Column('artist_id',  db.Integer, db.ForeignKey('artists.id'), primary_key=True)
)

class Artist(UserMixin, db.Model):
    __tablename__ = 'artists'
    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(100), nullable=False)
    email          = db.Column(db.String(120), nullable=False, unique=True)
    phone_number   = db.Column(db.String(20), nullable=True)
    address        = db.Column(db.String(200), nullable=True)
    password_hash  = db.Column(db.String(128), nullable=False)
    push_token     = db.Column(db.String(200), nullable=True)  # for push notifications
    is_admin       = db.Column(db.Boolean, default=False)
    price_min      = db.Column(db.Integer, default=1500)
    price_max      = db.Column(db.Integer, default=1900)

    # Many-to-many relationship to BookingRequest
    bookings       = db.relationship(
        'BookingRequest',
        secondary=booking_artists,
        back_populates='artists'
    )

    def set_password(self, pw: str):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw: str) -> bool:
        return check_password_hash(self.password_hash, pw)

class BookingRequest(db.Model):
    __tablename__ = 'booking_requests'
    id                 = db.Column(db.Integer, primary_key=True)
    client_name        = db.Column(db.String(100), nullable=False)
    client_email       = db.Column(db.String(120), nullable=False)

    # NEU: Event-Daten
    event_type         = db.Column(db.String(50), nullable=False)   # Cooperate, Privat, Incentive, Streetshow
    show_type          = db.Column(db.String(20), nullable=False)
    team_size          = db.Column(db.String(10), nullable=False)   
    number_of_guests   = db.Column(db.Integer, nullable=True)       
    event_address      = db.Column(db.String(200), nullable=True)   
    is_indoor          = db.Column(db.Boolean, default=True)        # Indoor (True) / Outdoor (False)
    event_date         = db.Column(db.Date, nullable=False)         # Date
    event_time         = db.Column(db.Time, nullable=True)          
    duration_minutes   = db.Column(db.Integer, nullable=False)     
    special_requests   = db.Column(db.Text, nullable=True)          

    needs_light        = db.Column(db.Boolean, default=False)
    needs_sound        = db.Column(db.Boolean, default=False)
    needs_fog          = db.Column(db.Boolean, default=False)

    distance_km        = db.Column(db.Float, nullable=False, default=0.0)
    newsletter_opt_in  = db.Column(db.Boolean, default=False)
    price_min          = db.Column(db.Integer, nullable=True)
    price_max          = db.Column(db.Integer, nullable=True)
    price_offered      = db.Column(db.Integer, nullable=True)
    status             = db.Column(db.String(20), default='requested')

    # Booking <-> Artist many-to-many
    artists          = db.relationship(
        'Artist',
        secondary=booking_artists,
        back_populates='bookings'
    )

class Availability(db.Model):
    __tablename__ = 'availabilities'
    id           = db.Column(db.Integer, primary_key=True)
    artist_id    = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable=False)
    date         = db.Column(db.Date, nullable=False)  # full-day availability slot

    # relationship back to Artist
    artist       = db.relationship(
        'Artist',
        backref=db.backref('availabilities', cascade='all, delete-orphan')
    )