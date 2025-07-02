import pytest
from managers.artist_manager import ArtistManager
from models import Artist

def test_get_all_artists_initially_empty():
    """Gibt eine leere Liste zurück, wenn keine Artists existieren."""
    manager = ArtistManager()
    artists = manager.get_all_artists()
    assert isinstance(artists, list)
    assert len(artists) == 0

def test_create_artist_and_get_all_artists():
    """Legt einen Artist an und prüft, dass er in der Gesamtliste erscheint."""
    manager = ArtistManager()
    artist = manager.create_artist('Max', 'max@example.com', 'secret', ['Zauberer'])
    artists = manager.get_all_artists()
    assert len(artists) == 1
    assert artists[0].id == artist.id
    assert artists[0].email == 'max@example.com'

def test_get_artist_by_email():
    """Sucht einen Artist per E-Mail und stellt sicher, dass er gefunden wird."""
    manager = ArtistManager()
    email = 'anne@example.com'
    artist = manager.create_artist('Anne', email, 'secret', ['Cyr-Wheel'])
    fetched = manager.get_artist_by_email(email)
    assert fetched is not None
    assert fetched.id == artist.id
    assert fetched.email == email