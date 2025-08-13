from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin 
from datetime import datetime

db = SQLAlchemy()

# Association-Tabelle: Many-to-Many zwischen BookingRequest und Artist
# mit zusätzlichem Feld 'requested_gage' für das angefragte Honorar.
booking_artists = db.Table(
    'booking_artists',
    db.Column('booking_id', db.Integer, db.ForeignKey('booking_requests.id'), primary_key=True),
    db.Column('artist_id',  db.Integer, db.ForeignKey('artists.id'), primary_key=True),
    db.Column('requested_gage', db.Integer, nullable=True),
    db.Column('status', db.String(20), nullable=False, server_default='angefragt'),
    db.Column('comment', db.Text, nullable=True)
)


# Association-Tabelle: Many-to-Many zwischen Artist und Discipline.
artist_disciplines = db.Table(
    'artist_disciplines',
    db.Column('artist_id', db.Integer, db.ForeignKey('artists.id'), primary_key=True),
    db.Column('discipline_id', db.Integer, db.ForeignKey('disciplines.id'), primary_key=True)
)


class Discipline(db.Model):
    """Disziplin, z. B. 'Zauberer' oder 'Cyr-Wheel', die einem Artist zugeordnet werden kann."""
    __tablename__ = 'disciplines'
    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)


class Artist(UserMixin, db.Model):
    """Artist-Profil mit persönlichen Daten, Login-Info, öffentlichem Profil (Bild & Bio) und Beziehungen zu Disziplinen und Buchungsanfragen."""
    __tablename__ = 'artists'
    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(100), nullable=False)
    email          = db.Column(db.String(120), nullable=False, unique=True)
    phone_number   = db.Column(db.String(20), nullable=True)
    address        = db.Column(db.String(200), nullable=True)
    password_hash  = db.Column(db.Text(), nullable=False)
    push_token     = db.Column(db.String(200), nullable=True)  # for push notifications
    is_admin       = db.Column(db.Boolean, default=False)
    price_min      = db.Column(db.Integer, default=1500)
    price_max      = db.Column(db.Integer, default=1900)
    supabase_user_id = db.Column(db.String(255), unique=True, nullable=True)

    # Admin-Freigabe
    approval_status  = db.Column(db.String(20), nullable=False, server_default='unsubmitted')  # unsubmitted | pending | approved | rejected
    rejection_reason = db.Column(db.Text, nullable=True)
    approved_at      = db.Column(db.DateTime, nullable=True)
    approved_by      = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable=True)

    # Beziehung: Admin, der den Artist freigegeben/abgelehnt hat (self-referenziell)
    approved_by_admin = db.relationship('Artist', foreign_keys=[approved_by], remote_side=[id])

    # Öffentliches Profil
    profile_image_url = db.Column(db.String(512), nullable=True)
    bio               = db.Column(db.Text, nullable=True)
    instagram = db.Column(db.String(255), nullable=True)
    gallery_urls = db.Column(db.JSON, nullable=True, default=list)


    # Beziehung: Ein Artist kann mehrere Disziplinen haben, und jede Disziplin kann mehreren Artists zugeordnet sein.
    disciplines    = db.relationship(
        'Discipline',
        secondary=artist_disciplines,
        backref='artists'
    )

    # Beziehung: Ein Artist kann in mehreren Buchungsanfragen involviert sein und umgekehrt.
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
    """Buchungsanfrage eines Clients mit Details wie Datum, Ort, Disziplinen und zugeordnete Artists."""
    __tablename__ = 'booking_requests'
    id                 = db.Column(db.Integer, primary_key=True)
    client_name        = db.Column(db.String(100), nullable=False)
    client_email       = db.Column(db.String(120), nullable=False)

    event_type         = db.Column(db.String(50), nullable=False)   # z.B. privat
    show_type          = db.Column(db.String(50), nullable=False)  # z.B. Walking Act oder Bühnen Show
    show_discipline    = db.Column(db.Text, nullable=False)
    team_size          = db.Column(db.String(10), nullable=False)   
    number_of_guests   = db.Column(db.Integer, nullable=True)       
    event_address      = db.Column(db.String(200), nullable=True)   
    is_indoor          = db.Column(db.Boolean, default=True)       
    event_date         = db.Column(db.Date, nullable=False)         
    event_time         = db.Column(db.Time, nullable=True)          
    duration_minutes   = db.Column(db.Integer, nullable=False)     
    special_requests   = db.Column(db.Text, nullable=True)          

    needs_light        = db.Column(db.Boolean, default=False)
    needs_sound        = db.Column(db.Boolean, default=False)

    distance_km        = db.Column(db.Float, nullable=False, default=0.0)
    newsletter_opt_in  = db.Column(db.Boolean, default=False)
    price_min          = db.Column(db.Integer, nullable=True)
    price_max          = db.Column(db.Integer, nullable=True)
    price_offered      = db.Column(db.Integer, nullable=True)
    artist_gage        = db.Column(db.Integer, nullable=True)
    artist_offer_date  = db.Column(db.DateTime, nullable=True)
    status             = db.Column(db.String(20), default='angefragt')

    # Beziehung: Eine Buchungsanfrage kann mehrere Artists involvieren und vice versa.
    artists          = db.relationship(
        'Artist',
        secondary=booking_artists,
        back_populates='bookings'
    )

class Availability(db.Model):
    """Verfügbarkeitstag eines Artists für (ganztägige) Buchungen."""
    __tablename__ = 'availabilities'
    __table_args__ = (
        db.UniqueConstraint('artist_id', 'date', name='uq_artist_date'),
    )
    id           = db.Column(db.Integer, primary_key=True)
    artist_id    = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable=False)
    date         = db.Column(db.Date, nullable=False)  # full-day availability slot

    # Beziehung: Ein Artist besitzt mehrere Verfügbarkeitstage.
    artist       = db.relationship(
        'Artist',
        backref=db.backref('availabilities', cascade='all, delete-orphan')
    )


class AdminOffer(db.Model):
    """Verwaltungs-Angebot eines Admin-Users für eine Buchungsanfrage."""
    __tablename__ = 'admin_offers'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('booking_requests.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable=False)
    override_price = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Beziehung: Eine Buchungsanfrage kann mehrere AdminOffers haben.
    request = db.relationship(
        'BookingRequest',
        backref=db.backref('admin_offers', cascade='all, delete-orphan')
    )
    # Beziehung: Ein Admin (Artist) kann mehrere AdminOffers erstellen.
    admin = db.relationship(
        'Artist',
        backref=db.backref('admin_offers', cascade='all, delete-orphan')
    )