import pytest
from sqlalchemy.pool import NullPool
from app import app as flask_app
from models import db as _db
from datamanager import DataManager
from sqlalchemy.orm import sessionmaker, scoped_session


@pytest.fixture(scope='session')
def app():
    """Verwendet eine frische In-Memory-Datenbank für Tests (NullPool verhindert Locks)."""
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'poolclass': NullPool,
        'connect_args': {'check_same_thread': False}
    }
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.drop_all()




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