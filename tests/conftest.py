import pytest
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sqlalchemy.pool import NullPool
from app import app as flask_app
from models import db, Artist
from sqlalchemy.orm import sessionmaker, scoped_session
from managers.artist_manager import ArtistManager
from managers.booking_requests_manager import BookingRequestManager
from config import TestConfig
from flask_jwt_extended import create_access_token
from sqlalchemy import event
import uuid
from werkzeug.security import generate_password_hash

def unique_email(prefix="user"):
    return f"{prefix}+{uuid.uuid4().hex[:8]}@example.com"


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


        # Tabellen genau auf DIESER Connection erstellen
        metadata = getattr(db, "metadata", None) or db.Model.metadata
        metadata.create_all(bind=conn)

        for table in reversed(metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()

        # 👉 KEINE root_trans hier! Nur Connection bereitstellen
        flask_app.config['TEST_DB_CONN'] = conn
        flask_app.config['TEST_DB_METADATA'] = metadata

        yield flask_app

        # Aufräumen am Ende der Session
        try:
            metadata.drop_all(bind=conn)
        finally:
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


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture()
def admin_headers(app):
    with app.app_context():
        token = create_access_token(
            identity="admin-user-fixture",
            additional_claims={"role": "admin", "app_metadata": {"role": "admin"}}
        )
    return _bearer(token)

@pytest.fixture()
def user_headers(app):
    with app.app_context():
        token = create_access_token(identity="test-user-regular")
    return _bearer(token)


# Führt jeden Test in einer eigenen Transaktion aus und rollt sie zurück.

@pytest.fixture(autouse=True)
def session_transaction(app):
    """
    Pro Test eine Nested-Transaktion (SAVEPOINT) auf der Session.
    Wenn innerhalb des Tests ein commit() passiert, legen wir automatisch
    einen neuen SAVEPOINT an, sodass der Test isoliert bleibt.
    """
    conn = app.config['TEST_DB_CONN']

    # Session-Factory auf DIESE Connection binden
    SessionFactory = sessionmaker(bind=conn)
    Session = scoped_session(SessionFactory)

    # Flask-SQLAlchemy global session auf unsere Test-Session zeigen lassen
    db.session = Session

    # Eine konkrete Session-Instanz ziehen
    sess = Session()

    # 👉 SAVEPOINT auf der SESSION (nicht auf der Connection!)
    nested = sess.begin_nested()

    # Wenn ein commit() in der Testlogik passiert, re-initialisieren wir den SAVEPOINT
    @event.listens_for(sess, "after_transaction_end")
    def _restart_savepoint(session, transaction):
        # Nur reagieren, wenn der beendete Transaction-Context der nested SAVEPOINT war
        if transaction.nested and not session.in_transaction():
            try:
                session.begin_nested()
            except Exception:
                pass

    try:
        yield
    finally:
        # Aufräumen in umgekehrter Reihenfolge
        try:
            if nested.is_active:
                nested.rollback()
        finally:
            Session.remove()
            
@pytest.fixture()
def artist_pending(app):
    """Gibt NUR die ID zurück, kein detached ORM-Objekt."""
    with app.app_context():
        a = Artist(
            name="Pending Paula",
            email=unique_email("pending"),
            supabase_user_id="user-pending-" + uuid.uuid4().hex[:6],
            approval_status="pending",
            password_hash=generate_password_hash("testpass"),
        )
        db.session.add(a)
        db.session.commit()
        return a.id  # ← nur die ID

@pytest.fixture()
def artist_approved(app):
    """Gibt NUR die ID zurück, kein detached ORM-Objekt."""
    with app.app_context():
        a = Artist(
            name="Approved Alex",
            email=unique_email("approved"),
            supabase_user_id="user-approved-" + uuid.uuid4().hex[:6],
            approval_status="approved",
            password_hash=generate_password_hash("testpass"),
        )
        db.session.add(a)
        db.session.commit()
        return a.id  # ← nur die ID

@pytest.fixture()
def get_artist(app):
    def _get(artist_id: int) -> Artist | None:
        with app.app_context():
            return Artist.query.get(artist_id)
    return _get
