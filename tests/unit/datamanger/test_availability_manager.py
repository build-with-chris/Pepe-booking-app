import pytest
from datetime import date, timedelta
from managers.availability_manager import AvailabilityManager
from managers.artist_manager import ArtistManager

def test_new_artist_has_full_year_availability():
    """Ein neuer Artist erhält standardmäßig 365 Verfügbarkeits-Tage."""
    artist_mgr = ArtistManager()
    manager = AvailabilityManager()
    artist = artist_mgr.create_artist('Test', 'test@ex.de', 'pw', ['Zauberer'])
    slots = manager.get_availabilities(artist.id)
    assert len(slots) == 365
    # Prüfe, dass der erste Tag heute ist und der letzte heute+364
    today = date.today()
    dates = sorted([slot.date for slot in slots])
    assert dates[0] == today
    assert dates[-1] == today + timedelta(days=364)

def test_add_availability_creates_slot():
    """add_availability fügt einen Slot hinzu, wenn er nicht existiert."""
    artist_mgr = ArtistManager()
    manager = AvailabilityManager()
    artist = artist_mgr.create_artist('A', 'a@ex.de', 'pw', ['Zauberer'])
    # Entferne alle Slots
    for slot in manager.get_availabilities(artist.id):
        manager.remove_availability(slot.id)
    # Jetzt keine Slots mehr
    assert manager.get_availabilities(artist.id) == []
    # Füge einen Slot für morgen hinzu
    tomorrow = date.today() + timedelta(days=1)
    slot = manager.add_availability(artist.id, tomorrow)
    assert slot.artist_id == artist.id
    assert slot.date == tomorrow
    # Doppelter Eintrag ändert nichts
    slot2 = manager.add_availability(artist.id, tomorrow)
    assert slot2.id == slot.id
    assert len(manager.get_availabilities(artist.id)) == 1

def test_remove_availability():
    """remove_availability löscht einen vorhandenen Slot oder gibt None zurück."""
    artist_mgr = ArtistManager()
    manager = AvailabilityManager()
    artist = artist_mgr.create_artist('B', 'b@ex.de', 'pw', ['Zauberer'])
    slots = manager.get_availabilities(artist.id)
    slot = slots[0]
    removed = manager.remove_availability(slot.id)
    assert removed.id == slot.id
    # Erneutes Löschen gibt None
    assert manager.remove_availability(slot.id) is None