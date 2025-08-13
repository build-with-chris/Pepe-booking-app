import pytest
from sqlalchemy.pool import NullPool
from app import app as flask_app
from models import db, Artist
from sqlalchemy.orm import sessionmaker, scoped_session
from managers.artist_manager import ArtistManager
from managers.booking_requests_manager import BookingRequestManager
from config import TestConfig
from flask_jwt_extended import create_access_token




@pytest.fixture(scope='session')
def app():
    flask_app.config['TESTING'] = True
    flask_app.config.from_object(TestConfig)
    flask_app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'poolclass': NullPool,
        'connect_args': {'check_same_thread': False}
    }
    flask_app.config['SERVER_NAME'] = 'localhost'
    flask_app.config['PREFERRED_URL_SCHEME'] = 'http'

    with flask_app.app_context():
        # Eine Connection für die ganze Testsuite
        conn = db.engine.connect()
        # Tabellen mit GENAU DIESER Connection anlegen
        db.create_all(bind=conn)

        # Connection für spätere Fixtures verfügbar machen
        flask_app.config['TEST_DB_CONN'] = conn

        yield flask_app

        # Aufräumen am Ende der Session
        db.drop_all(bind=conn)
        conn.close()

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

def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


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
    resp = client.post('/auth/login', json={'email': 'adminuser@test.de', 'password': 'adminpass'})
    
    token = resp.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture()
def user_headers(app):
    """JWT-Header für normalen User (ohne Adminrechte)."""
    with app.app_context():
        token = create_access_token(identity="test-user-regular")
    return _bearer(token)



# Führt jeden Test in einer eigenen Transaktion aus und rollt sie zurück.
@pytest.fixture(autouse=True)
def session_transaction(app):
    """Führt jeden Test in einer eigenen Transaktion aus und rollt sie zurück."""
    # Dieselbe Conn wie im app()-Fixture
    conn = app.config['TEST_DB_CONN']

    trans = conn.begin()
    SessionLocal = scoped_session(sessionmaker(bind=conn))
    db.session = SessionLocal

    yield

    SessionLocal.remove()
    trans.rollback()
    # WICHTIG: conn NICHT hier schließen – das macht das app()-Fixture am Ende!

@pytest.fixture()
def artist_pending(app):
    """Legt einen Artist mit Status 'pending' an und gibt ihn zurück."""
    with app.app_context():
        a = Artist(
            name="Pending Paula",
            email="paula@example.com",
            supabase_user_id="user-pending-1",
            approval_status="pending",
        )
        db.session.add(a)
        db.session.commit()
        return a

@pytest.fixture()
def artist_approved(app):
    """Legt einen freigegebenen Artist (approved) an und gibt ihn zurück."""
    with app.app_context():
        a = Artist(
            name="Approved Alex",
            email="alex@example.com",
            supabase_user_id="user-approved-1",
            approval_status="approved",
        )
        db.session.add(a)
        db.session.commit()
        return a