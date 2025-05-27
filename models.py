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
    password_hash  = db.Column(db.String(128), nullable=False)
    push_token     = db.Column(db.String(200), nullable=True)  # for push notifications
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
    id               = db.Column(db.Integer, primary_key=True)
    client_name      = db.Column(db.String(100), nullable=False)
    client_email     = db.Column(db.String(120), nullable=False)
    event_date       = db.Column(db.Date, nullable=False)
    duration_hours   = db.Column(db.Integer, nullable=False)  # Event duration in hours
    show_type        = db.Column(db.String(50), nullable=False)  # solo/duo/team
    status           = db.Column(db.String(20), default='requested')
    distance_km      = db.Column(db.Float, nullable=False, default=0.0)
    newsletter_opt_in= db.Column(db.Boolean, default=False)
    price_min        = db.Column(db.Integer, nullable=True)
    price_max        = db.Column(db.Integer, nullable=True)
    price_offered    = db.Column(db.Integer, nullable=True)

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