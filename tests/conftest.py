import pytest
from sqlalchemy.pool import NullPool
from app import app as flask_app
from models import db as _db
from sqlalchemy.orm import sessionmaker, scoped_session
from managers.artist_manager import ArtistManager
from managers.booking_requests_manager import BookingRequestManager
from flask import url_for
from config import TestConfig



@pytest.fixture(scope='session')
def app():
    """Verwendet eine frische In-Memory-Datenbank für Tests (NullPool verhindert Locks)."""
    flask_app.config['TESTING'] = True
    flask_app.config.from_object(TestConfig)
    flask_app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'poolclass': NullPool,
        'connect_args': {'check_same_thread': False}
    }
    # Configure URL building for tests
    flask_app.config['SERVER_NAME'] = 'localhost'
    flask_app.config['PREFERRED_URL_SCHEME'] = 'http'
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.drop_all()

@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()

@pytest.fixture
def artist_manager(app):
    """ArtistManager instance."""
    return ArtistManager()

@pytest.fixture
def booking_request_manager(app):
    """BookingRequestManager instance."""
    return BookingRequestManager()

@pytest.fixture
def auth_headers(client, artist_manager):
    """
    Create a test user, log in via the auth endpoint, and return authorization headers.
    """
    # Create a test artist/user
    artist = artist_manager.create_artist('AuthTest', 'auth@test.de', 'pass', ['Zauberer'])
    # Log in to get token
    resp = client.post('/auth/login', json={'email': 'auth@test.de', 'password': 'pass'})
    token = resp.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def admin_auth_headers(client, artist_manager):
    """
    Create an admin user via ArtistManager, log in, and return headers with a valid admin Bearer token.
    """
    # Create admin user
    admin = artist_manager.create_artist(
        name='AdminUser',
        email='adminuser@test.de',
        password='adminpass',
        disciplines=['Zauberer'],
        is_admin=True
    )
    # Log in to get token
    resp = client.post(
        url_for('auth.login'),
        json={'email': 'adminuser@test.de', 'password': 'adminpass'}
    )
    token = resp.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}

@pytest.fixture
def db(app):
    """Return SQLAlchemy db."""
    return _db


# Führt jeden Test in einer eigenen Transaktion aus und rollt sie zurück.
@pytest.fixture(autouse=True)
def session_transaction(app):
    """Führt jeden Test in einer eigenen Transaktion aus und rollt sie zurück."""
    conn = _db.engine.connect()
    trans = conn.begin()
    # Binde die Session an diese Connection mithilfe scoped_session
    SessionLocal = scoped_session(sessionmaker(bind=conn))
    _db.session = SessionLocal

    yield

    SessionLocal.remove()
    trans.rollback()
    conn.close()

@pytest.fixture
def dm(app):
    """Gibt eine frische DataManager-Instanz pro Test."""
    return DataManager()