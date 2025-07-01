import pytest
from datetime import date, timedelta
from datamanager import DataManager

def test_new_artist_has_full_year_availability(dm):
    """Ein neuer Artist erhält standardmäßig 365 Verfügbarkeits-Tage."""
    artist = dm.create_artist('Test', 'test@ex.de', 'pw', ['Zauberer'])
    slots = dm.get_availabilities(artist.id)
    assert len(slots) == 365
    # Prüfe, dass der erste Tag heute ist und der letzte heute+364
    today = date.today()
    dates = sorted([slot.date for slot in slots])
    assert dates[0] == today
    assert dates[-1] == today + timedelta(days=364)

def test_add_availability_creates_slot(dm):
    """add_availability fügt einen Slot hinzu, wenn er nicht existiert."""
    artist = dm.create_artist('A', 'a@ex.de', 'pw', ['Zauberer'])
    # Entferne alle Slots
    for slot in dm.get_availabilities(artist.id):
        dm.remove_availability(slot.id)
    # Jetzt keine Slots mehr
    assert dm.get_availabilities(artist.id) == []
    # Füge einen Slot für morgen hinzu
    tomorrow = date.today() + timedelta(days=1)
    slot = dm.add_availability(artist.id, tomorrow)
    assert slot.artist_id == artist.id
    assert slot.date == tomorrow
    # Doppelter Eintrag ändert nichts
    slot2 = dm.add_availability(artist.id, tomorrow)
    assert slot2.id == slot.id
    assert len(dm.get_availabilities(artist.id)) == 1

def test_remove_availability(dm):
    """remove_availability löscht einen vorhandenen Slot oder gibt None zurück."""
    artist = dm.create_artist('B', 'b@ex.de', 'pw', ['Zauberer'])
    slots = dm.get_availabilities(artist.id)
    slot = slots[0]
    removed = dm.remove_availability(slot.id)
    assert removed.id == slot.id
    # Erneutes Löschen gibt None
    assert dm.remove_availability(slot.id) is None