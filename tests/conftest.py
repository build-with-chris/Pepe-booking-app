import pytest
from app import app as flask_app
from models import db as _db
from datamanager import DataManager


@pytest.fixture(scope='session')
def app():
    """Verwendet eine In-Memory SQLite-Datenbank für Tests."""
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.drop_all()


# AUTOUSE: Setzt die Datenbank vor jedem Test zurück.
@pytest.fixture(autouse=True)
def reset_database(app):
    """Setzt die Datenbank vor jedem Test zurück."""
    _db.drop_all()
    _db.create_all()

@pytest.fixture
def dm(app):
    """Gibt eine frische DataManager-Instanz pro Test."""
    return DataManager()