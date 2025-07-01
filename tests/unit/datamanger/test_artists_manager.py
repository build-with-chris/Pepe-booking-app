import pytest
from datamanager import DataManager
from models import Artist

def test_get_all_artists_initially_empty(dm):
    """Gibt eine leere Liste zurück, wenn keine Artists existieren."""
    artists = dm.get_all_artists()
    assert isinstance(artists, list)
    assert len(artists) == 0

def test_create_artist_and_get_all_artists(dm):
    """Legt einen Artist an und prüft, dass er in der Gesamtliste erscheint."""
    artist = dm.create_artist('Max', 'max@example.com', 'secret', ['Zauberer'])
    artists = dm.get_all_artists()
    assert len(artists) == 1
    assert artists[0].id == artist.id
    assert artists[0].email == 'max@example.com'

def test_get_artist_by_email(dm):
    """Sucht einen Artist per E-Mail und stellt sicher, dass er gefunden wird."""
    email = 'anne@example.com'
    artist = dm.create_artist('Anne', email, 'secret', ['Cyr-Wheel'])
    fetched = dm.get_artist_by_email(email)
    assert fetched is not None
    assert fetched.id == artist.id
    assert fetched.email == email