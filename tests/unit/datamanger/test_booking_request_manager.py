import pytest
from datetime import date
from managers.booking_requests_manager import BookingRequestManager
from managers.artist_manager import ArtistManager
from models import Artist, BookingRequest

def test_create_and_get_request():
    """Legt eine Buchungsanfrage an und prüft get_request und get_all_requests."""
    booking_mgr = BookingRequestManager()
    artist_mgr = ArtistManager()
    artist = artist_mgr.create_artist('Tester', 't@ex.de', 'pw', ['Zauberer'])
    req = booking_mgr.create_request(
        client_name      = 'Client',
        client_email     = 'client@ex.de',
        event_date       = date.today().isoformat(),
        duration_minutes = 10,
        event_type       = 'Private Feier',
        show_discipline  = ['Zauberer'],
        team_size        = 1,
        number_of_guests = 5,
        event_address    = 'Musterstr. 1',
        is_indoor        = True,
        special_requests = 'None',
        needs_light      = False,
        needs_sound      = False,
        artists          = [artist]
    )
    # Prüfen, dass die Anfrage gespeichert und abrufbar ist
    fetched = booking_mgr.get_request(req.id)
    assert isinstance(fetched, BookingRequest)
    assert fetched.client_email == 'client@ex.de'
    all_reqs = booking_mgr.get_all_requests()
    assert any(r.id == req.id for r in all_reqs)

def test_set_offer_solo():
    """Solo-Booking direktes Angebot und Status 'angeboten'."""
    booking_mgr = BookingRequestManager()
    artist_mgr = ArtistManager()
    artist = artist_mgr.create_artist('Solo', 'solo@ex.de', 'pw', ['Zauberer'])
    req = booking_mgr.create_request(
        client_name      = 'C',
        client_email     = 'c@ex.de',
        event_date       = date.today().isoformat(),
        duration_minutes = 5,
        event_type       = 'Private Feier',
        show_discipline  = ['Zauberer'],
        team_size        = 1,
        number_of_guests = 10,
        event_address    = 'Ort',
        is_indoor        = True,
        special_requests = '',
        needs_light      = False,
        needs_sound      = False,
        artists          = [artist]
    )
    updated = booking_mgr.set_offer(req.id, artist.id, 500)
    assert updated.status == 'angeboten'
    # Bei Solo-Booking wird die Agenturgebühr von 20% aufgerechnet: 500 × 1.2 = 600
    assert updated.price_offered == 600

def test_set_offer_multiple():
    """Duo-Booking erst nach beiden Angeboten 'angeboten'."""
    booking_mgr = BookingRequestManager()
    artist_mgr = ArtistManager()
    a1 = artist_mgr.create_artist('A1', 'a1@ex.de', 'pw', ['Zauberer'])
    a2 = artist_mgr.create_artist('A2', 'a2@ex.de', 'pw', ['Zauberer'])
    req = booking_mgr.create_request(
        client_name      = 'DuoClient',
        client_email     = 'duo@ex.de',
        event_date       = date.today().isoformat(),
        duration_minutes = 15,
        event_type       = 'Private Feier',
        show_discipline  = ['Zauberer'],
        team_size        = 2,
        number_of_guests = 20,
        event_address    = 'Ort2',
        is_indoor        = False,
        special_requests = '',
        needs_light      = False,
        needs_sound      = False,
        artists          = [a1, a2]
    )
    # Erst nach erstem Angebot noch nicht final
    first = booking_mgr.set_offer(req.id, a1.id, 300)
    assert first.status != 'angeboten'
    # Nach zweitem Angebot final
    second = booking_mgr.set_offer(req.id, a2.id, 400)
    assert second.status == 'angeboten'
    assert isinstance(second.price_offered, (int, float))

def test_change_status():
    """Ändert status bei gültigem Status; unzulässiger bleibt unverändert."""
    booking_mgr = BookingRequestManager()
    artist_mgr = ArtistManager()
    artist = artist_mgr.create_artist('CS', 'cs@ex.de', 'pw', ['Zauberer'])
    req = booking_mgr.create_request(
        client_name      = 'Change',
        client_email     = 'change@ex.de',
        event_date       = date.today().isoformat(),
        duration_minutes = 20,
        event_type       = 'Private Feier',
        show_discipline  = ['Zauberer'],
        team_size        = 1,
        number_of_guests = 10,
        event_address    = 'Ort3',
        is_indoor        = True,
        special_requests = '',
        needs_light      = False,
        needs_sound      = False,
        artists          = [artist]
    )
    # Gültiger Statuswechsel
    updated = booking_mgr.change_status(req.id, 'akzeptiert')
    assert updated.status == 'akzeptiert'
    # Ungültiger Status wird ignoriert
    unchanged = booking_mgr.change_status(req.id, 'ungültiger_status')
    assert unchanged.status == 'akzeptiert'